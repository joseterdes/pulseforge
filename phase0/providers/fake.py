"""Fake provider: a kick-drum click track at the spec's BPM. Tests the pipeline without a GPU."""
import math
import wave
from array import array

from _common import run_worker

SAMPLE_RATE = 44100
HIT_SECONDS = 0.12


def load(_args):
    return None


def render(_model, job: dict, out_wav) -> str:
    bpm = job["spec"]["bpm"]
    total = int(job["duration_s"] * SAMPLE_RATE)
    samples = array("h", bytes(2 * total))
    beat = 60.0 / bpm
    hit_len = int(HIT_SECONDS * SAMPLE_RATE)
    for b in range(int(job["duration_s"] / beat) + 1):
        start = int(b * beat * SAMPLE_RATE)
        for i in range(min(hit_len, total - start)):
            t = i / SAMPLE_RATE
            samples[start + i] = int(20000 * math.exp(-t * 30) * math.sin(2 * math.pi * 60 * t))
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(samples.tobytes())
    return f"fake click track at {bpm} BPM"


if __name__ == "__main__":
    run_worker("fake", load, render)
