# PulseForge

AI club-music app: users paste a song link or upload audio and get an original track with the same feel. Solo founder, $0 budget, based in the Philippines.

- **Plan (source of truth):** [docs/BLUEPRINT.md](docs/BLUEPRINT.md). Settled decisions are in §20; don't re-ask them.
- **Current status and next step:** [docs/STATUS.md](docs/STATUS.md). Update it at the end of each work session.
- **Phase 0 model test:** [phase0/README.md](phase0/README.md).

## Rules that come from the plan

- Never download audio from streaming or store links (Spotify, YouTube, etc.). Links only identify the song.
- Uploaded reference audio never goes into a music model. Only the style profile (BPM, key, tags, energy) does ("reference-audio firewall").
- MusicGen and other non-commercial weights are for benchmarks only, never production.
- Prefer free tiers and self-hosting; explain any paid service and give a free alternative.
- Beginner-first UX: plain words in Simple mode, details in Pro mode.

## Git workflow

- Repo: https://github.com/joseterdes/pulseforge (public, AGPL-3.0), owned by the `joseterdes` account. On a machine where `gh` has several accounts logged in, make sure `joseterdes` is active (`gh auth switch -u joseterdes`).
- Commits use GitHub's noreply email, set per repo: `git config user.email 275752389+joseterdes@users.noreply.github.com`. Never commit with a work email.
- `main` is protected. Work on a branch (`feat/…`, `fix/…`, `docs/…`, `chore/…`), open a PR with `gh pr create`, wait for CI (`lint`, `phase0`, `secrets`), then squash-merge.
- Never commit audio, model weights, `phase0/results/`, `phase0/envs/` or `.env` files.

## Backend (`backend/`)

- Setup: `docker compose -f infra/compose.yml up -d`, then `cd backend && uv sync --extra api`. Details in [backend/README.md](backend/README.md).
- Test: set `TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:54322/pulseforge_test`, then `cd backend && uv run pytest -v`.
- Migrate: `uv run alembic upgrade head`. Run: `uv run uvicorn pulseforge.api.main:app --reload`.
- Lint (repo root): `uvx ruff@0.17.3 check .`

## Machines

- Laptop: no NVIDIA GPU. Use the `fake` provider.
- Home PC: RTX 3060 12 GB, 16 GB RAM, Windows 11. Model work runs in Ubuntu on WSL2, with the project at `~/pulseforge`.
