#!/usr/bin/env python3
"""Phase 0 evaluation: automatic metrics, a blind listening set, and the report.

Run with the hf environment (it has librosa and pyloudnorm):

    envs/hf/bin/python evaluate.py metrics results/<run_id>   # BPM, key, loudness, clipping per clip
    envs/hf/bin/python evaluate.py blind   results/<run_id>   # shuffled clips + rating sheet
    envs/hf/bin/python evaluate.py report  results/<run_id>   # report.md from everything above
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import statistics
import sys
from pathlib import Path

import numpy as np

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# Krumhansl-Kessler key profiles, index 0 = tonic.
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
ANALYSIS_SR = 22050
BPM_TOLERANCE = 2.0
CLIPPING_PCT_LIMIT = 0.1
# Only ACE-Step renders long tracks, so including them would reveal the provider.
BLIND_MAX_SECONDS = 60
RATING_FIELDS = ["overall_1to5", "club_feel_1to5", "matches_request_1to5"]


def load_specs() -> dict[str, dict]:
    specs = json.loads((Path(__file__).parent / "specs.json").read_text(encoding="utf-8"))["specs"]
    return {s["id"]: s for s in specs}


def load_records(run_dir: Path) -> list[dict]:
    """Latest result per (provider, job), so a retried job replaces its earlier failure."""
    records: dict[tuple[str, str], dict] = {}
    for path in sorted(run_dir.glob("*/results.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                records[(r["provider"], r["job_id"])] = r
    return list(records.values())


def estimate_key(y: np.ndarray, sr: int) -> str:
    import librosa

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
    best_score, best_key = -2.0, "unknown"
    for tonic in range(12):
        for mode, profile in (("major", MAJOR), ("minor", MINOR)):
            score = float(np.nan_to_num(np.corrcoef(chroma, np.roll(profile, tonic))[0, 1], nan=-1.0))
            if score > best_score:
                best_score, best_key = score, f"{NOTES[tonic]} {mode}"
    return best_key


def estimate_tempo(y: np.ndarray, sr: int) -> float:
    """Tempo to within ~0.5 BPM from the onset envelope's autocorrelation.

    librosa's own estimate is snapped to analysis-frame steps (126 BPM reads as
    123.0), too coarse for a ±2 BPM check. Instead, score every tempo from 70 to
    200 BPM in 0.05 steps by the autocorrelation at 1, 2, 4 and 8 beats; the
    longer spans make small tempo differences show up clearly.
    """
    import librosa

    hop = 512
    env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    env = env - env.mean()
    autocorr = np.correlate(env, env, "full")[len(env) - 1:]
    bpms = np.arange(70.0, 200.0, 0.05)
    lags = 60.0 * (sr / hop) / bpms
    frames = np.arange(len(autocorr))
    score = sum(np.interp(k * lags, frames, autocorr, right=0.0) for k in (1, 2, 4, 8))
    return float(bpms[np.argmax(score)])


def relative_key(key: str) -> str:
    note, mode = key.split()
    i = NOTES.index(note)
    return f"{NOTES[(i + 3) % 12]} major" if mode == "minor" else f"{NOTES[(i - 3) % 12]} minor"


def analyze(path: Path, spec: dict) -> dict:
    import librosa
    import pyloudnorm as pyln
    import soundfile as sf

    y, sr = sf.read(path, always_2d=True)
    mono = y.mean(axis=1)
    frame = int(0.05 * sr)
    n_frames = max(1, len(mono) // frame)
    rms = np.sqrt((mono[: n_frames * frame].reshape(n_frames, frame) ** 2).mean(axis=1) + 1e-12)
    y22 = librosa.resample(mono, orig_sr=sr, target_sr=ANALYSIS_SR)
    tempo = estimate_tempo(y22, ANALYSIS_SR)
    key = estimate_key(y22, ANALYSIS_SR)
    if key == spec["key"]:
        key_match = "exact"
    elif key == relative_key(spec["key"]):
        key_match = "relative"
    else:
        key_match = "no"
    return {
        "duration_s": round(len(mono) / sr, 2),
        "sample_rate": sr,
        "channels": y.shape[1],
        "lufs": round(float(pyln.Meter(sr).integrated_loudness(y)), 1),
        "peak_dbfs": round(float(20 * np.log10(np.abs(y).max() + 1e-12)), 1),
        "clipping_pct": round(100 * float((np.abs(y) >= 0.999).mean()), 3),
        "silence_pct": round(100 * float((20 * np.log10(rms) < -50).mean()), 1),
        "bpm_detected": round(tempo, 1),
        # Beat trackers often lock onto half or double time; that is still the right groove.
        "bpm_error": round(min(abs(tempo * f - spec["bpm"]) for f in (0.5, 1.0, 2.0)), 1),
        "key_detected": key,
        "key_match": key_match,
    }


def cmd_metrics(run_dir: Path) -> None:
    specs = load_specs()
    records = [r for r in load_records(run_dir) if r.get("ok")]
    metrics = {}
    for i, r in enumerate(records, 1):
        print(f"[{i}/{len(records)}] {r['provider']}/{r['job_id']}", flush=True)
        metrics[f"{r['provider']}/{r['job_id']}"] = analyze(run_dir / r["provider"] / r["wav"], specs[r["spec_id"]])
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Wrote {run_dir / 'metrics.json'}")


def cmd_blind(run_dir: Path) -> None:
    listening = run_dir / "listening"
    if listening.exists():
        sys.exit(f"{listening} already exists; delete it first if you really want a new shuffle "
                 "(this discards the clip numbering your ratings refer to).")
    specs = load_specs()
    clips = [r for r in load_records(run_dir) if r.get("ok") and r["duration_s"] <= BLIND_MAX_SECONDS]
    random.shuffle(clips)
    listening.mkdir()
    key, rows = {}, []
    for n, r in enumerate(clips, 1):
        clip = f"{n:03d}"
        shutil.copy(run_dir / r["provider"] / r["wav"], listening / f"{clip}.wav")
        key[clip] = {"provider": r["provider"], "job_id": r["job_id"]}
        s = specs[r["spec_id"]]
        rows.append({"clip": clip,
                     "asked_for": f"{s['genre']}, {s['bpm']} BPM, {s['key']}, {', '.join(s['moods'])}",
                     **{f: "" for f in RATING_FIELDS}, "artifacts_yes_no": "", "notes": ""})
    (run_dir / "blind_key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    with (listening / "ratings_TEMPLATE.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["clip"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(clips)} clips in {listening}")
    print("Copy ratings_TEMPLATE.csv to ratings_<yourname>.csv, listen, and fill it in (1 = bad, 5 = great).")
    print("Don't open blind_key.json until all ratings are done.")


def median(values: list[float]) -> str:
    return f"{statistics.median(values):.1f}" if values else "–"


def mean(values: list[float]) -> str:
    return f"{statistics.mean(values):.2f}" if values else "–"


def pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f}%" if whole else "–"


def load_ratings(run_dir: Path) -> dict[str, dict[str, list[float]]]:
    """provider -> rating field -> scores, from every listening/ratings_<name>.csv."""
    key_path = run_dir / "blind_key.json"
    if not key_path.exists():
        return {}
    key = json.loads(key_path.read_text(encoding="utf-8"))
    ratings: dict[str, dict[str, list[float]]] = {}
    for sheet in sorted((run_dir / "listening").glob("ratings_*.csv")):
        if sheet.stem == "ratings_TEMPLATE":
            continue
        with sheet.open(newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                provider = key.get(row.get("clip", "").zfill(3), {}).get("provider")
                if not provider:
                    continue
                for field in RATING_FIELDS:
                    value = (row.get(field) or "").strip()
                    if value:
                        ratings.setdefault(provider, {}).setdefault(field, []).append(float(value))
    return ratings


def cmd_report(run_dir: Path) -> None:
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    records = load_records(run_dir)
    metrics_path = run_dir / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
    ratings = load_ratings(run_dir)
    providers = sorted({r["provider"] for r in records})

    lines = [f"# Phase 0 report: {meta['run_id']}", "",
             f"GPU: {meta['gpu']}  ", f"Started: {meta['started']}  ",
             f"Quick run: {'yes' if meta['quick'] else 'no'}", "",
             "## Speed and reliability (clips up to 60 s)", "",
             "| Provider | Commercial use | Jobs ok | Model load (s) | Median gen time (s) | Median speed (x realtime) | Peak VRAM (GB) |",
             "|---|---|---|---|---|---|---|"]
    for p in providers:
        rs = [r for r in records if r["provider"] == p]
        short = [r for r in rs if r.get("ok") and r["duration_s"] <= BLIND_MAX_SECONDS]
        commercial = meta["providers"].get(p, {}).get("commercial_ok")
        lines.append("| {} | {} | {}/{} | {} | {} | {} | {} |".format(
            p, "yes" if commercial else "**no (NC license)**",
            sum(1 for r in rs if r.get("ok")), len(rs),
            median([r["load_seconds"] for r in rs if r.get("ok")]),
            median([r["gen_seconds"] for r in short]),
            median([r["speed_x_realtime"] for r in short]),
            max((r["peak_vram_gb"] for r in rs if "peak_vram_gb" in r), default="–")))

    lines += ["", "## Automatic quality checks", "",
              f"| Provider | Median BPM error | BPM within ±{BPM_TOLERANCE:g} | Key exact | Key exact or relative | Mean LUFS | Clips clipping > {CLIPPING_PCT_LIMIT}% |",
              "|---|---|---|---|---|---|---|"]
    for p in providers:
        ms = [m for k, m in metrics.items() if k.split("/", 1)[0] == p]
        lines.append("| {} | {} | {} | {} | {} | {} | {} |".format(
            p, median([m["bpm_error"] for m in ms]),
            pct(sum(m["bpm_error"] <= BPM_TOLERANCE for m in ms), len(ms)),
            pct(sum(m["key_match"] == "exact" for m in ms), len(ms)),
            pct(sum(m["key_match"] != "no" for m in ms), len(ms)),
            mean([m["lufs"] for m in ms if np.isfinite(m["lufs"])]),
            sum(m["clipping_pct"] > CLIPPING_PCT_LIMIT for m in ms)))
    if not metrics:
        lines.append("\n_No metrics yet: run `evaluate.py metrics` first._")

    lines += ["", "## Blind listening ratings (1–5)", "",
              "| Provider | Overall | Club feel | Matches request | Ratings |", "|---|---|---|---|---|"]
    for p in providers:
        pr = ratings.get(p, {})
        lines.append(f"| {p} | {mean(pr.get('overall_1to5', []))} | {mean(pr.get('club_feel_1to5', []))} | "
                     f"{mean(pr.get('matches_request_1to5', []))} | {len(pr.get('overall_1to5', []))} |")
    if not ratings:
        lines.append("\n_No ratings yet: run `evaluate.py blind`, then fill in listening/ratings_<name>.csv._")

    long_runs = [r for r in records if r.get("ok") and r["duration_s"] > BLIND_MAX_SECONDS]
    if long_runs:
        lines += ["", "## Long-form renders (listen to these separately)", "",
                  "| Provider | Job | Gen time (s) | Speed (x realtime) | Peak VRAM (GB) |", "|---|---|---|---|---|"]
        lines += [f"| {r['provider']} | {r['job_id']} | {r['gen_seconds']} | {r['speed_x_realtime']} | "
                  f"{r.get('peak_vram_gb', '–')} |" for r in long_runs]

    failures = [r for r in records if not r.get("ok")]
    if failures:
        lines += ["", "## Failures", ""] + [f"- `{r['provider']}/{r['job_id']}`: {r['error']}" for r in failures]

    report = "\n".join(lines) + "\n"
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {run_dir / 'report.md'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["metrics", "blind", "report"])
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    if not (args.run_dir / "run.json").exists():
        sys.exit(f"{args.run_dir} is not a benchmark run (no run.json)")
    {"metrics": cmd_metrics, "blind": cmd_blind, "report": cmd_report}[args.command](args.run_dir)


if __name__ == "__main__":
    main()
