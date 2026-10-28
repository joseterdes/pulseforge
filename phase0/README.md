# Phase 0: model test

**Goal:** before building the app, find out whether open music models can make club tracks good enough for PulseForge, how fast they run on the RTX 3060, and which one becomes the default. This is the go/no-go gate in [docs/BLUEPRINT.md §12](../docs/BLUEPRINT.md).

## What gets tested

| Model | Can we ship it? | Clips |
|---|---|---|
| **ACE-Step** | Yes (Apache-2.0) | 10 styles × 2 seeds × 30 s, plus three 3-minute tracks |
| **Stable Audio Open 1.0** | Yes (free under $1M revenue) | 10 styles × 2 seeds × 30 s |
| **MusicGen medium** | **No** (non-commercial). Reference point only. | 10 styles × 2 seeds × 30 s |

The 10 styles are in [specs.json](specs.json): deep house, tech house, peak-time techno, melodic techno, trance, liquid drum & bass, afro house, amapiano, UK garage and disco house.

For every clip the kit records:
- **Speed:** model load time, generation time, speed vs. real time, peak GPU memory
- **Automatic checks:** detected BPM vs. requested, detected key vs. requested, loudness, clipping
- **Your ears:** a blind listening test, where clips are shuffled and numbered so you don't know which model made which.

## Steps

First-time setup on the home PC: follow **[SETUP_HOME_PC.md](SETUP_HOME_PC.md)**. It takes about 1–2 hours, mostly downloads.

Then, inside Ubuntu, from the `phase0` folder:

```bash
python3 bench.py run --quick          # 1. smoke test: 2 short clips per model (~10 min incl. model downloads)
python3 bench.py run                  # 2. full test (~1–2 hours; leave the PC alone)

RUN=results/<run id printed above>
envs/hf/bin/python evaluate.py metrics $RUN   # 3. automatic checks
envs/hf/bin/python evaluate.py blind   $RUN   # 4. makes $RUN/listening/ with numbered clips
#    5. copy listening/ratings_TEMPLATE.csv to ratings_<yourname>.csv and rate every clip
envs/hf/bin/python evaluate.py report  $RUN   # 6. writes $RUN/report.md
```

**Listening on Windows:** in Ubuntu, run `explorer.exe $RUN/listening` to open the folder in File Explorer. The rating sheet opens in Excel or Google Sheets; save it as CSV. Use headphones or decent speakers, and rate each clip 1–5 for overall quality, club feel, and how well it matches what was asked for. If two DJ friends rate too (each with their own `ratings_<name>.csv`), the report averages everyone. Don't open `blind_key.json` until all ratings are in.

The three 3-minute ACE-Step tracks are left out of the blind test because their length would reveal the model. Listen to them separately in `$RUN/ace_step/`.

If a run stops halfway, continue it with `python3 bench.py run --resume <run id>`; finished clips are skipped.

## How to decide

The default model is the **commercially usable** model with the best average "overall" rating, as long as it also meets all of these:

- [ ] average **overall ≥ 3.0** and **club feel ≥ 3.0**
- [ ] median **BPM error ≤ 2 BPM** (post-processing can time-stretch small errors, but not a wrong groove)
- [ ] a **3-minute track renders in ≤ 3 minutes** on the RTX 3060 (ACE-Step only; Stable Audio Open tops out at 47 s)
- [ ] no crashes with normal settings.

**If no model passes:** full-track generation isn't ready yet. Pivot the MVP to loops and short clips, Stable Audio Open's strength, and revisit when new models appear.

**If MusicGen clearly beats both shippable models:** note it. It means fine-tuning a shippable model (planned for v2) matters more, but MusicGen itself still can't be used.

Write the conclusion to **`phase0/RESULTS.md`**: the chosen default model, the key numbers from `report.md`, and anything surprising you heard.

## Troubleshooting

| Problem | Fix |
|---|---|
| `CUDA out of memory` from ACE-Step | `python3 bench.py run --resume <run id> --providers ace_step --ace-cpu-offload` |
| Stable Audio Open: `401` / `gated repo` | Accept the license on its Hugging Face page and log in (SETUP step 6) |
| ACE-Step errors about arguments or imports | Its API may have changed since this kit was written. Ask Claude Code to fix `providers/ace_step.py` by reading the installed `acestep` package; the rest of the kit doesn't need to change. |
| Whole PC freezes or Ubuntu gets killed | RAM is full. Close games and browsers, and check `.wslconfig` (SETUP step 1). |
| `nvidia-smi` fails inside Ubuntu | Update the Windows NVIDIA driver, then run `wsl --shutdown` in PowerShell and reopen Ubuntu. Never install a Linux NVIDIA driver inside WSL. |

## Files

| File | What it does |
|---|---|
| `specs.json` | The 10 test styles |
| `bench.py` | Runs every model on every style (standard library only) |
| `providers/*.py` | One small adapter per model, plus `fake.py`, which tests the pipeline without a GPU |
| `evaluate.py` | Automatic checks, blind listening set, report |
| `setup_envs.sh` | Creates the two Python environments (`envs/hf`, `envs/ace_step`) |
| `results/` | Everything generated (not committed to git) |
