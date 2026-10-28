# PulseForge status

_Last updated: 2026-10-28_

## Where we are

- **Architecture plan:** done, see [BLUEPRINT.md](BLUEPRINT.md) (v0.2). Settled decisions are listed in §20.
- **Phase 0 (model test):** the kit is ready in [phase0/](../phase0/README.md) and was tested end-to-end on the laptop with the fake provider. It has **not yet run on a real GPU.**
- **Backend foundation (M1a):** done. FastAPI in [backend/](../backend/README.md) with Supabase login-token checks, Postgres + migrations, health checks and `/v1/me`.
- **Next, in order:**
  1. Local MVP plan on the laptop: [docs/superpowers/plans/2026-10-28-local-mvp.md](superpowers/plans/2026-10-28-local-mvp.md).
  2. Phase 0 on the home PC: set up ([phase0/SETUP_HOME_PC.md](../phase0/SETUP_HOME_PC.md)), run the smoke test, run the full benchmark, do the blind listening test, and write `phase0/RESULTS.md` with the chosen default model.
  3. **M1b** (web app + Supabase login): needs a free Supabase project in Singapore.
  4. **M1c** (deploy): needs Oracle Cloud, Cloudflare and Sentry accounts.

## Machines

| Machine | Specs | Role |
|---|---|---|
| Laptop | i5-12450H, 16 GB RAM, Intel UHD (no NVIDIA GPU), Docker Desktop on WSL2 | Day-to-day app development with the `fake` provider |
| Home PC | Ryzen 5 5600X, **RTX 3060 12 GB**, 16 GB RAM, Windows 11, ~220 GB free disk | Phase 0, model work, main GPU worker during the beta (Modal as fallback) |

## Decisions so far (details in BLUEPRINT §20)

1. Audience: everyone, beginners first, with Simple mode and Pro mode.
2. Public GitHub repo [joseterdes/pulseforge](https://github.com/joseterdes/pulseforge), AGPL-3.0, with a protected `main` (PRs + CI).
3. Region: Singapore.
4. GPU: home RTX 3060 for Phase 0 and the beta, Modal as fallback.
5. Song input: paste a link from any platform (identity only, no audio download) or upload audio. The default result is "inspired by"; true remix only later, for owned or licensed uploads.

## Open items

- [ ] Oracle Cloud home region: Singapore first, Tokyo or Osaka as fallback
- [ ] Trademark search for "PulseForge" (IPOPHL, USPTO)
- [ ] Phase 0 results → `phase0/RESULTS.md`

## Phase 0 kit: known risks

- `phase0/providers/ace_step.py` targets the ACE-Step v1 Python API from memory; the installed version may differ. It drops unknown arguments automatically, but may still need a small fix after installing.
- Stable Audio Open and MusicGen use the standard `diffusers` / `transformers` APIs and are lower risk.
- The real-GPU code paths (all three models) have only been written, not run. The runner, the evaluation and the report were verified with the fake provider.
