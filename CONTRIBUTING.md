# Contributing

Thanks for your interest! PulseForge is early: the plan is in [docs/BLUEPRINT.md](docs/BLUEPRINT.md) and the current focus is in [docs/STATUS.md](docs/STATUS.md). For anything bigger than a small fix, please open an issue first so we can agree on the approach.

## Workflow

`main` is protected: every change goes through a pull request, and CI must pass before it's merged.

1. Create a branch: `git switch -c feat/short-description` (use the prefix `fix/`, `docs/` or `chore/` as fits).
2. Make the change and run the checks below.
3. Open a pull request that says what changed and why.
4. Once CI is green, the PR is **squash-merged** and the branch is deleted.

## Checks to run locally

```bash
pip install ruff==0.17.3 && ruff check .   # same version as CI
cd phase0 && python3 bench.py run --providers fake --quick   # pipeline smoke test, no GPU needed
```

CI also runs the evaluation step and a secret scan (gitleaks).

## Ground rules

- **Never commit copyrighted audio**, model weights, generated results, `.env` files or credentials. `.gitignore` covers the usual paths; GitHub push protection blocks known secret formats.
- Test audio must be openly licensed (e.g. Creative Commons from Freesound or the Free Music Archive), with the source noted.
- Keep the reference-audio firewall: uploaded or linked songs may only produce a style profile and must never be passed to a generation model (see BLUEPRINT §4.2 and §17).
- Contributions are accepted under the project's license, [AGPL-3.0](LICENSE).
