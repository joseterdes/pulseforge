#!/usr/bin/env bash
# Creates the two isolated Python environments for the Phase 0 benchmark.
# ACE-Step pins its own library versions, so it gets an environment of its own.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_VERSION=3.10

echo "== hf environment: MusicGen + Stable Audio Open + evaluation tools =="
uv venv --python "$PYTHON_VERSION" envs/hf
uv pip install --python envs/hf torch
# torchsde is needed by Stable Audio Open's sampler in diffusers.
uv pip install --python envs/hf transformers diffusers accelerate sentencepiece torchsde \
  soundfile librosa pyloudnorm "huggingface_hub[cli]"
uv pip freeze --python envs/hf > envs/hf.freeze.txt

echo "== ace_step environment =="
uv venv --python "$PYTHON_VERSION" envs/ace_step
uv pip install --python envs/ace_step torch torchaudio
uv pip install --python envs/ace_step "git+https://github.com/ace-step/ACE-Step.git"
uv pip freeze --python envs/ace_step > envs/ace_step.freeze.txt

echo "== checking the GPU from both environments =="
for env in hf ace_step; do
  envs/$env/bin/python -c "import torch; print('$env:', torch.__version__, 'CUDA OK' if torch.cuda.is_available() else 'NO GPU', torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
done
echo "Done. Next: python3 bench.py run --quick"
