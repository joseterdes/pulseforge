"""Shared plumbing for Phase 0 provider workers.

A worker loads its model once, renders every job in a jobs file, and appends
one JSON line per job to results.jsonl. A provider module only supplies
load(args) and render(model, job, out_wav) -> prompt, mirroring the provider
adapters planned in docs/BLUEPRINT.md section 4.3.
"""
from __future__ import annotations

import argparse
import inspect
import json
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any


def log(name: str, message: str) -> None:
    print(f"[{name}] {message}", flush=True)


def cuda():
    """torch if a CUDA GPU is usable, else None (the fake provider runs without torch)."""
    try:
        import torch
    except ImportError:
        return None
    return torch if torch.cuda.is_available() else None


def supported_kwargs(fn: Callable, wanted: dict[str, Any], name: str) -> dict[str, Any]:
    """Keep only the keyword arguments fn accepts, so small upstream API changes don't crash the run."""
    params = inspect.signature(fn).parameters
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return wanted
    dropped = sorted(set(wanted) - set(params))
    if dropped:
        log(name, f"note: {fn.__qualname__} does not accept {', '.join(dropped)}; using its defaults")
    return {k: v for k, v in wanted.items() if k in params}


def run_worker(name: str, load: Callable, render: Callable,
               add_args: Callable[[argparse.ArgumentParser], None] | None = None) -> None:
    parser = argparse.ArgumentParser(description=f"Phase 0 worker: {name}")
    parser.add_argument("--jobs", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    if add_args:
        add_args(parser)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    jobs = json.loads(args.jobs.read_text(encoding="utf-8"))
    torch = cuda()

    start = time.perf_counter()
    model = load(args)
    load_s = time.perf_counter() - start
    log(name, f"model ready in {load_s:.1f}s")

    with (args.out / "results.jsonl").open("a", encoding="utf-8") as fh:
        for i, job in enumerate(jobs, 1):
            out_wav = args.out / f"{job['job_id']}.wav"
            record = {"provider": name, "job_id": job["job_id"], "spec_id": job["spec"]["id"],
                      "duration_s": job["duration_s"], "seed": job["seed"],
                      "load_seconds": round(load_s, 1), "wav": out_wav.name}
            if torch:
                torch.cuda.reset_peak_memory_stats()
                torch.cuda.synchronize()
            start = time.perf_counter()
            try:
                prompt = render(model, job, out_wav)
                if torch:
                    torch.cuda.synchronize()
                gen_s = time.perf_counter() - start
                if not out_wav.exists():
                    raise RuntimeError(f"provider finished but wrote no file at {out_wav.name}")
                record.update(ok=True, prompt=prompt, gen_seconds=round(gen_s, 2),
                              speed_x_realtime=round(job["duration_s"] / gen_s, 2))
                if torch:
                    record["peak_vram_gb"] = round(torch.cuda.max_memory_allocated() / 1e9, 2)
            except Exception as exc:  # noqa: BLE001 - one bad job must not stop the benchmark
                traceback.print_exc()
                record.update(ok=False, error=f"{type(exc).__name__}: {exc}")
                if torch:
                    torch.cuda.empty_cache()
            fh.write(json.dumps(record) + "\n")
            fh.flush()
            status = f"ok in {record['gen_seconds']}s" if record["ok"] else "FAILED"
            log(name, f"[{i}/{len(jobs)}] {job['job_id']}: {status}")
