"""Stable Audio Open 1.0 (diffusers). Gated on Hugging Face: accept the license on the model page first."""
from _common import run_worker

MODEL_ID = "stabilityai/stable-audio-open-1.0"
MAX_SECONDS = 47.0
STEPS = 100
NEGATIVE = "vocals, singing, low quality, distorted, muffled, noise"


def build_prompt(spec: dict) -> str:
    parts = [spec["genre"], f"{spec['bpm']} BPM", spec["key"], *spec["instruments"], *spec["moods"],
             "club mix", "high quality"]
    return ", ".join(parts)


def load(_args):
    import torch
    from diffusers import StableAudioPipeline

    return StableAudioPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.float16).to("cuda")


def render(pipe, job: dict, out_wav) -> str:
    import soundfile as sf
    import torch

    prompt = build_prompt(job["spec"])
    generator = torch.Generator("cuda").manual_seed(job["seed"])
    audio = pipe(
        prompt,
        negative_prompt=NEGATIVE,
        num_inference_steps=STEPS,
        audio_end_in_s=min(float(job["duration_s"]), MAX_SECONDS),
        num_waveforms_per_prompt=1,
        generator=generator,
    ).audios
    sf.write(out_wav, audio[0].T.float().cpu().numpy(), pipe.vae.sampling_rate)
    return prompt


if __name__ == "__main__":
    run_worker("stable_audio_open", load, render)
