"""ACE-Step (Apache-2.0), installed from its GitHub repo.

This adapter targets the ACE-Step v1 Python API (acestep.pipeline_ace_step.ACEStepPipeline).
It is the part of Phase 0 most likely to need adjusting if the installed version
differs: supported_kwargs() drops arguments the installed version no longer
accepts, and the output file is found by searching the job's temp folder rather
than assuming a filename.
"""
import shutil
import tempfile
from pathlib import Path

from _common import log, run_worker, supported_kwargs

AUDIO_EXTS = (".wav", ".flac", ".ogg", ".mp3")
INFER_STEPS = 60
GUIDANCE = 15.0


def build_tags(spec: dict) -> str:
    parts = [spec["genre"], f"{spec['bpm']} bpm", spec["key"], *spec["instruments"], *spec["moods"],
             "instrumental", "club mix"]
    return ", ".join(parts)


def add_args(parser) -> None:
    parser.add_argument("--cpu-offload", action="store_true")


def generate(pipe, tags: str, seconds: float, seed: int, out_dir: Path) -> Path:
    wanted = {
        "format": "wav",
        "audio_duration": float(seconds),
        "prompt": tags,
        "lyrics": "[instrumental]",
        "infer_step": INFER_STEPS,
        "guidance_scale": GUIDANCE,
        "manual_seeds": [seed],
        "save_path": str(out_dir),
    }
    pipe(**supported_kwargs(pipe.__call__, wanted, "ace_step"))
    produced = sorted((p for p in out_dir.rglob("*") if p.suffix.lower() in AUDIO_EXTS),
                      key=lambda p: p.stat().st_mtime)
    if not produced:
        raise RuntimeError(f"ACE-Step wrote no audio into {out_dir}")
    return produced[-1]


def load(args):
    from acestep.pipeline_ace_step import ACEStepPipeline

    wanted = {"dtype": "bfloat16", "torch_compile": False, "cpu_offload": args.cpu_offload}
    pipe = ACEStepPipeline(**supported_kwargs(ACEStepPipeline.__init__, wanted, "ace_step"))
    # ACE-Step loads its checkpoint lazily, so a short warm-up render makes
    # the reported load time real and keeps it out of the first job's timing.
    log("ace_step", "warming up (downloads the checkpoint on first run, ~8 GB)")
    with tempfile.TemporaryDirectory() as tmp:
        generate(pipe, "house, 124 bpm, instrumental", 5, 0, Path(tmp))
    return pipe


def render(pipe, job: dict, out_wav: Path) -> str:
    tags = build_tags(job["spec"])
    with tempfile.TemporaryDirectory() as tmp:
        produced = generate(pipe, tags, job["duration_s"], job["seed"], Path(tmp))
        if produced.suffix.lower() == ".wav":
            shutil.move(str(produced), out_wav)
        else:
            import torchaudio

            audio, sr = torchaudio.load(str(produced))
            torchaudio.save(str(out_wav), audio, sr)
    return tags


if __name__ == "__main__":
    run_worker("ace_step", load, render, add_args)
