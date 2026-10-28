# Home PC setup for Phase 0

For the home PC: Windows 11, AMD Ryzen 5 5600X, **RTX 3060 12 GB**, 16 GB RAM.
Everything runs inside **Ubuntu on WSL2**. That's the same Linux environment the app will use in production, and the one every music model is tested on.

Plan for about 1–2 hours, mostly downloads (~25–30 GB in total). Commands in grey boxes are copied and pasted; each step says whether it goes in **PowerShell** (Windows) or **Ubuntu**.

---

## 1. Give WSL enough memory (PowerShell)

By default, WSL gets only half the RAM (8 GB), which is too little to load these models. Create the file `C:\Users\<you>\.wslconfig`:

```powershell
notepad "$env:USERPROFILE\.wslconfig"
```

Paste this, save, and close:

```ini
[wsl2]
memory=12GB
swap=16GB
```

That leaves Windows 4 GB while WSL is busy, so **close games, Discord and big browser sessions during the benchmark.**

## 2. Update the NVIDIA driver (Windows)

Install the latest **Game Ready** or **Studio** driver from the NVIDIA App or nvidia.com. Then check it in PowerShell:

```powershell
nvidia-smi
```

It should list **NVIDIA GeForce RTX 3060** with about **12288MiB** of memory.

## 3. Install Ubuntu on WSL2 (PowerShell as Administrator)

```powershell
wsl --install -d Ubuntu-24.04
```

Restart if asked, then open **Ubuntu** from the Start menu and create a Linux username and password. If WSL was already installed, run `wsl --update` and then `wsl --shutdown` so the new memory setting applies.

**Disk space:** WSL stores Ubuntu on drive C:. If C: has less than ~60 GB free, move it to a bigger drive (PowerShell): `wsl --shutdown`, then `wsl --manage Ubuntu-24.04 --move E:\WSL`.

## 4. Check the GPU and install tools (Ubuntu)

```bash
nvidia-smi                      # must show the RTX 3060; do NOT install any NVIDIA driver inside Ubuntu
sudo apt update && sudo apt install -y git ffmpeg build-essential
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv --version
```

## 5. Get the PulseForge code into Ubuntu

Keep the project inside Ubuntu's own disk (`~/pulseforge`), not under `/mnt/c/...`. Files on the Windows drive are many times slower for Linux tools.

**Option A, GitHub (recommended):**

```bash
git clone https://github.com/joseterdes/pulseforge.git ~/pulseforge
cd ~/pulseforge
git config user.name "Jose"
git config user.email "275752389+joseterdes@users.noreply.github.com"
```

To push changes from this PC later, install the GitHub CLI in Ubuntu (`sudo apt install gh`), then run `gh auth login` and choose the **joseterdes** account.

**Option B, copy the folder.** Bring the `PulseForge` folder from the laptop on a USB stick or through Google Drive, put it on the Windows desktop, then:

```bash
cp -r /mnt/c/Users/<windows-user>/Desktop/PulseForge ~/pulseforge
```

## 6. Hugging Face account (browser + Ubuntu)

Stable Audio Open is free but gated: you have to accept its license once.

1. Create a free account at huggingface.co.
2. Open the **stabilityai/stable-audio-open-1.0** model page and accept the license.
3. Go to **Settings → Access Tokens**, create a token with **Read** access, and copy it.

You'll log in at the end of step 7.

## 7. Create the Python environments (Ubuntu)

```bash
cd ~/pulseforge/phase0
bash setup_envs.sh
```

This takes 10–20 minutes. The last lines should say **CUDA OK** and **NVIDIA GeForce RTX 3060** for both environments. Then log in to Hugging Face and paste the token when asked:

```bash
envs/hf/bin/hf auth login
```

(On an older version of the tool, the command is `envs/hf/bin/huggingface-cli login`.)

## 8. Smoke test (Ubuntu)

```bash
python3 bench.py run --quick
```

The first run downloads the models (~20 GB), so it takes a while. When it finishes, every model should show `ok` for its two clips. If something fails, check the troubleshooting table in [README.md](README.md). If ACE-Step is the one failing, that's expected to be the most likely spot, and Claude Code can fix it on the spot.

## 9. Optional: Claude Code on the home PC

This lets us continue the work there:

1. Install **VS Code** on Windows, plus the **WSL** extension and the **Claude Code** extension.
2. In Ubuntu, run `code ~/pulseforge`. VS Code opens the project inside WSL.
3. Ask Claude: *"Read docs/STATUS.md and continue Phase 0."* The repo's `CLAUDE.md` and `docs/STATUS.md` carry everything decided so far. Claude's memory from the laptop doesn't travel to another PC.

Then go to [README.md](README.md) and run the full benchmark.
