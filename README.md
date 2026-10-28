# PulseForge

**Make an original club track that feels like the songs you love.** Paste a link from Spotify, YouTube, Apple Music, SoundCloud, Beatport and others, or upload audio. PulseForge works out the tempo, key, genre and energy, and generates a new track with the same feel, using open-source music models.

> **Status: pre-alpha.** We're in Phase 0, testing which open music model is good enough to build on. There is no app to use yet.

## How it works

```
link or upload ──▶ analysis (BPM, key, genre, energy) ──▶ style profile ──▶ open music model ──▶ original track
```

- **Original, never a copy.** Your reference songs are only measured. Their audio never goes into the music model; only the style profile does. Every result is also checked for close similarity to the references.
- **Links identify, they don't download.** A Spotify or YouTube link tells us which song it is, and the musical data comes from open databases.
- **Open models, swappable.** ACE-Step and Stable Audio Open sit behind one interface, so better models can be dropped in later.
- **Made for beginners and DJs.** Simple mode uses plain words and vibe presets; Pro mode adds BPM and key locks and DJ-ready intros and outros.

## Repository

| Path | What's there |
|---|---|
| [docs/BLUEPRINT.md](docs/BLUEPRINT.md) | The full technical plan: architecture, AI pipeline, data model, API, roadmap, legal |
| [docs/STATUS.md](docs/STATUS.md) | Where the project is right now and what's next |
| [phase0/](phase0/README.md) | Model test kit: benchmark open music models on a local GPU, with a blind listening test |

## Running the Phase 0 test

You need an NVIDIA GPU with 12 GB of memory and Windows with WSL2, or Linux. Follow [phase0/SETUP_HOME_PC.md](phase0/SETUP_HOME_PC.md), then [phase0/README.md](phase0/README.md). Without a GPU, you can still try the pipeline with the fake provider:

```bash
cd phase0 && python3 bench.py run --providers fake --quick
```

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md). Please report vulnerabilities privately, as described in [SECURITY.md](SECURITY.md).

## License

[GNU AGPL-3.0](LICENSE). You can use, study, modify and self-host PulseForge. If you run a modified version as a service for others, you must publish your changes under the same license.

The AI models PulseForge downloads have their own licenses. MusicGen's weights are non-commercial and are used only in the Phase 0 benchmark; see [docs/BLUEPRINT.md §17](docs/BLUEPRINT.md).
