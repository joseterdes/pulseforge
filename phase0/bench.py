#!/usr/bin/env python3
"""Phase 0 benchmark runner.

Expands specs.json into generation jobs, runs each provider in its own
virtualenv (their dependencies conflict), and collects everything under
results/<run_id>/. Standard library only, so any python3 can run it.

    python3 bench.py run --quick              # smoke test: 2 short clips per provider
    python3 bench.py run                      # full benchmark
    python3 bench.py run --providers ace_step # one provider only
    python3 bench.py run --resume <run_id>    # retry jobs that have no audio yet
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# env=None means "the python running this script": the fake provider needs no packages.
PROVIDERS = {
    "ace_step": {"env": "ace_step", "max_seconds": 240, "long_form": True, "commercial_ok": True},
    "stable_audio_open": {"env": "hf", "max_seconds": 47, "long_form": False, "commercial_ok": True},
    "musicgen": {"env": "hf", "max_seconds": 30, "long_form": False, "commercial_ok": False},
    "fake": {"env": None, "max_seconds": 600, "long_form": True, "commercial_ok": True},
}
DEFAULT_PROVIDERS = ["ace_step", "stable_audio_open", "musicgen"]
CLIP_SECONDS = 30
LONG_SECONDS = 180
QUICK_SECONDS = 10
SEEDS = [1, 2]


def build_jobs(specs: list[dict], provider: str, quick: bool) -> list[dict]:
    cfg = PROVIDERS[provider]
    if quick:
        return [make_job(spec, QUICK_SECONDS, SEEDS[0]) for spec in specs[:2]]
    clip = min(CLIP_SECONDS, cfg["max_seconds"])
    jobs = [make_job(spec, clip, seed) for spec in specs for seed in SEEDS]
    if cfg["long_form"]:
        jobs += [make_job(spec, LONG_SECONDS, SEEDS[0]) for spec in specs if spec.get("long")]
    return jobs


def make_job(spec: dict, seconds: int, seed: int) -> dict:
    return {
        "job_id": f"{spec['id']}__{seconds}s__seed{seed}",
        "spec": spec,
        "duration_s": seconds,
        "seed": seed,
    }


def python_for(env: str | None) -> str:
    if env is None:
        return sys.executable
    exe = ROOT / "envs" / env / "bin" / "python"
    if not exe.exists():
        sys.exit(f"Missing environment: {exe}\nRun first: bash setup_envs.sh")
    return str(exe)


def gpu_name() -> str:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "no NVIDIA GPU detected"


def cmd_run(args: argparse.Namespace) -> None:
    unknown = [p for p in args.providers if p not in PROVIDERS]
    if unknown:
        sys.exit(f"Unknown provider(s): {', '.join(unknown)}. Choose from: {', '.join(PROVIDERS)}")

    specs = json.loads((ROOT / "specs.json").read_text(encoding="utf-8"))["specs"]
    if args.resume:
        run_id = args.resume
    else:
        run_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S") + ("-quick" if args.quick else "")
    run_dir = ROOT / "results" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    meta_path = run_dir / "run.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        args.quick = meta["quick"]  # a resumed run keeps its original job list
    else:
        meta = {"run_id": run_id, "started": dt.datetime.now().isoformat(timespec="seconds"),
                "gpu": gpu_name(), "quick": args.quick, "providers": {}}
    for provider in args.providers:
        meta["providers"][provider] = PROVIDERS[provider]
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Run {run_id} on: {meta['gpu']}")

    for provider in args.providers:
        env = PROVIDERS[provider]["env"]
        out_dir = run_dir / provider
        out_dir.mkdir(exist_ok=True)
        jobs = [j for j in build_jobs(specs, provider, args.quick)
                if not (out_dir / f"{j['job_id']}.wav").exists()]
        if not jobs:
            print(f"\n=== {provider}: nothing left to do ===")
            continue

        jobs_file = out_dir / "jobs.json"
        jobs_file.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
        cmd = [python_for(env), str(ROOT / "providers" / f"{provider}.py"),
               "--jobs", str(jobs_file), "--out", str(out_dir)]
        if provider == "ace_step" and args.ace_cpu_offload:
            cmd.append("--cpu-offload")

        print(f"\n=== {provider}: {len(jobs)} jobs ===", flush=True)
        code = subprocess.run(cmd, check=False).returncode
        if code:
            print(f"!!! {provider} worker exited with code {code}; see the output above. "
                  f"Fix it, then: python3 bench.py run --resume {run_id} --providers {provider}")

        if env:
            freeze = ROOT / "envs" / f"{env}.freeze.txt"
            if freeze.exists():
                shutil.copy(freeze, run_dir / freeze.name)

    print(f"\nDone. Results in {run_dir}")
    print("Next:")
    print(f"  envs/hf/bin/python evaluate.py metrics results/{run_id}")
    print(f"  envs/hf/bin/python evaluate.py blind   results/{run_id}")
    print(f"  envs/hf/bin/python evaluate.py report  results/{run_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="generate audio for every spec with each provider")
    run.add_argument("--providers", nargs="+", default=DEFAULT_PROVIDERS)
    run.add_argument("--quick", action="store_true", help="smoke test: 2 specs, 1 seed, 10-second clips")
    run.add_argument("--resume", metavar="RUN_ID", help="continue an existing run, skipping finished jobs")
    run.add_argument("--ace-cpu-offload", action="store_true",
                     help="let ACE-Step move idle weights to system RAM (use if it runs out of GPU memory)")
    run.set_defaults(func=cmd_run)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
