"""MusicGen (transformers). Weights are CC-BY-NC: benchmark baseline only, never production."""
from _common import run_worker

MODEL_ID = "facebook/musicgen-medium"
MAX_TOKENS = 1500  # the model was trained on 30-second windows


def build_prompt(spec: dict) -> str:
    return (f"An instrumental {spec['genre']} club track at {spec['bpm']} BPM in {spec['key']}, "
            f"with {', '.join(spec['instruments'])}. {', '.join(spec['moods']).capitalize()} mood.")


def load(_args):
    import torch
    from transformers import AutoProcessor, MusicgenForConditionalGeneration

    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = MusicgenForConditionalGeneration.from_pretrained(MODEL_ID, torch_dtype=torch.float16).to("cuda")
    return processor, model


def render(loaded, job: dict, out_wav) -> str:
    import soundfile as sf
    import torch

    processor, model = loaded
    prompt = build_prompt(job["spec"])
    torch.manual_seed(job["seed"])
    inputs = processor(text=[prompt], padding=True, return_tensors="pt").to("cuda")
    audio_cfg = model.config.audio_encoder
    tokens = min(int(job["duration_s"] * audio_cfg.frame_rate), MAX_TOKENS)
    audio = model.generate(**inputs, do_sample=True, guidance_scale=3.0, max_new_tokens=tokens)
    sf.write(out_wav, audio[0, 0].float().cpu().numpy(), audio_cfg.sampling_rate)
    return prompt


if __name__ == "__main__":
    run_worker("musicgen", load, render)
