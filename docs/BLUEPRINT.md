# PulseForge — Technical Blueprint v0.2

> Status: architecture plan, pre-code. Date: 2026-10-28. v0.2 applies the founder decisions on audience, repo, region and GPU (see §20).
> Free-tier limits and model licenses change often. Every number marked *(verify)* must be re-checked on the day you sign up or pin a model version.

---

## 0. Summary of decisions

| Decision | Choice | One-line reason |
|---|---|---|
| Product wedge | **Beginner-first club music maker** (pick a vibe or upload songs you like → original track), with a **Pro mode** for DJ-ready output (steady BPM, mixable intro/outro, Camelot key) | Serves everyone from people who have never made music to working DJs. Pro mode covers a niche that generic AI-song apps ignore. |
| Default generator | **ACE-Step** (Apache-2.0) for full tracks; **Stable Audio Open** for loops and "clean-data mode" | Both can be used commercially. MusicGen's weights are **non-commercial** and stay dev-only. |
| Backend language | **Python (FastAPI)** everywhere server-side | The whole audio/ML stack is Python. One language means one set of types and one toolchain. |
| Frontend | **Next.js + TypeScript**, on **Cloudflare** | Free hosting that allows commercial use (unlike Vercel Hobby). |
| DB + Auth | **Supabase** (Postgres + Auth) | Database, auth and a dashboard in one free project. |
| Audio storage | **Cloudflare R2** | 10 GB free and **no egress fees**, which matters for an app that serves audio downloads. |
| Queue | **Postgres jobs table** (`SKIP LOCKED`) | No Redis to run or pay for. Workers anywhere can pull over HTTPS. |
| GPU | **Modal free monthly credits** for production, **Kaggle/Colab/local GPU** for dev and eval only | The only free GPU that may legitimately serve production traffic. |
| API + CPU workers host | **Oracle Cloud Always Free ARM VM** (4 cores / 24 GB) | The most generous always-on free compute. |
| Key architecture rule | **The reference-audio firewall**: uploaded audio never reaches the generator. Only an abstract *style profile* (numbers and tags) crosses. | This is both the copyright design and the provider-swap design. |
| Region | **Singapore** (Supabase, Oracle, R2 APAC hint) | Closest major cloud region to the Philippines (~30–50 ms from Manila). |
| Repo | **Public on GitHub ([joseterdes/pulseforge](https://github.com/joseterdes/pulseforge)), AGPL-3.0** | Free CI minutes and security tooling; AGPL stops someone hosting a closed copy. |
| Dev machine | Laptop with **no NVIDIA GPU** (Intel UHD, i5-12450H, 16 GB) → CPU dev with a fake provider | Everything except the big models runs locally. |
| GPU | **Home PC with an RTX 3060 12 GB** for Phase 0 and as the main beta GPU worker; **Modal** as automatic fallback and for the public launch; Kaggle as backup | The home PC joins the job queue like any other worker, with no inbound ports. |
| Song input | **Paste a link from any major platform** (Spotify, YouTube, Apple Music, SoundCloud, Deezer, Tidal, Beatport, Mixcloud, TikTok…) **or upload a file.** A link only identifies the song (title/artist → open music databases); no audio is downloaded. Platforms are plugins ("link resolvers"). | Streaming terms forbid downloading. Uploads give a closer match. |

---

## 1. Product

### 1.1 Vision
A DJ or producer uploads tracks, a DJ mix, or a set of tracks that stands in for a playlist. PulseForge learns the *vibe* (tempo, groove, energy arc, instrumentation, genre) and generates a **new, original** club track with that vibe. It never produces a copy.

### 1.2 Target users
Decided 2026-10-28: the app is for **everyone who likes club music, including people with no music experience**. One product serves three groups:

| Group | What they want | How PulseForge serves them |
|---|---|---|
| **Beginners and fans** (primary, largest) | "Make me a track that sounds like the songs I like", with no jargon | Simple mode: vibe presets or uploads, plain-language sliders, two previews, one tap to download |
| **Content creators** (first to pay) | Copyright-safe background music for videos and streams | A "what's it for?" picker sets length and loopable endings; **Clean mode** toggle |
| **Aspiring and working DJs / producers** | Tracks they can actually mix, sketches to finish in a DAW | Pro mode: full style-profile editor, exact BPM/key, DJ-ready intro/outro, prompt preview, later stems and MIDI |

Beginners win UX decisions. Pro features are layered on top and stay hidden until someone opts in. The product also can't depend on users owning reference tracks.

### 1.3 Experience: Simple mode and Pro mode

**Simple mode (default)** is a four-step wizard:
1. **Start from a vibe.** Pick a **vibe preset** (e.g. "Sunset Deep House", "Peak-time Techno", "Afro House Groove", "Amapiano", "Liquid Drum & Bass", "Budots" as an experimental local flavor) **or** upload 1–5 songs you like.
2. **What's it for?** "DJ set", "Video / stream background" or "Just for fun". This sets length, structure and endings.
3. **Tune it in plain words.** Energy (chill → hype), Mood (dark → bright), Length. No BPM or key jargon; tooltips explain the terms for the curious.
4. **Generate.** Two 30-second previews → pick one → full track → download MP3 (WAV in Pro mode).

**Pro mode** is a per-user toggle that is remembered. It exposes everything: BPM and key locks, Camelot keys, the style-profile editor, the structure template, the generated prompt, provider choice and Clean mode, and later stems and MIDI export.

**Vibe presets** are hand-written style profiles (§6) stored read-only. They use no audio and no copyrighted references, so they are legally clean and cost no analysis. They are the main path for beginners and the first thing a new user sees.

### 1.4 Differentiator: "DJ-ready" (Pro mode)
Generic text-to-music tools produce clips that drift in tempo and start and end abruptly. PulseForge outputs should:
- hold a constant, exact BPM (verified by analysis, corrected by time-stretch if needed)
- start and end with a 16 or 32-bar mostly-drums intro and outro for mixing
- report key in Camelot notation (8A, 5B…) for harmonic mixing
- have phrase-aligned sections (8/16/32 bars).

This is achievable with post-processing and arrangement logic on top of open models. A solo developer can build it, and big players don't focus on it.

### 1.5 Non-goals (MVP)
- Vocals and lyrics (they add voice-likeness legal risk and quality problems)
- Downloading audio from any streaming or store link. Links are accepted, but only to identify the song (§1.6, §5).
- Remixing commercial songs the user has no rights to (§1.6)
- Real-time generation, DAW plugin, mobile app
- Training our own foundation model.

### 1.6 Song input: links, uploads, and what "remix" means

Users can give PulseForge a song in two ways:

| Input | What we get | What we do with it |
|---|---|---|
| **Paste a link** from any major platform: Spotify, YouTube, YouTube Music, Apple Music, SoundCloud, Deezer, Tidal, Amazon Music, Beatport, Bandcamp, Mixcloud, TikTok and more (§5 Stage 0) | Only the song's identity: title and artist | Look up its BPM, key and genre in open music databases → style profile → new track. **No audio is downloaded.** |
| **Upload an audio file** | The actual sound | Full analysis (§5): BPM, key, energy curve, groove, structure → a more accurate style profile → new track |

A link is quicker and needs no file. An upload matches the feel more closely, and the UI says so: "For a closer match, upload the file."

**Why a link can't give us the audio:** Spotify streams are DRM-protected, and both Spotify's and YouTube's terms forbid downloading. A downloader built into the app would put the whole project at risk; the 2020 takedown of youtube-dl on GitHub happened for exactly this reason.

**Two kinds of result:**
- **"Inspired by" (default, MVP):** a brand-new track with the same feel (speed, key, genre, energy). Nothing from the original recording is in it, so it works with any song and is safe to post.
- **"Remix" (v1.2, uploads only):** keeps parts of the uploaded audio (for example the vocal, split out with Demucs) and builds a new beat around it in another genre or tempo. A remix is a derivative work, so this mode is only for music the user owns or may remix: their own productions, licensed sample packs, or tracks under a license that allows remixing (e.g. CC BY). It requires a rights confirmation per file, and results are labeled "private use unless you hold the rights". Remixing commercial songs without permission stays off-limits; releasing such a remix needs the label's permission.

**What the AI "knows":** the open music models were trained by their creators on large music collections. They have not learned the specific song a user pastes. PulseForge measures that song (or looks it up) and turns the measurements into instructions for the model. That is how the result gets the same feel without copying.

---

## 2. Facts that shape the design

These constraints drive the whole design. Read them before the rest of the document.

1. **MusicGen and AudioCraft weights are CC-BY-NC 4.0, so they can't be used commercially.** The AudioCraft code is MIT; the weights are not. MusicGen can be used for prototyping and internal evaluation, but it can never serve paying users. The same applies to MAGNeT, JASCO, and the MERT and Essentia models (see §17).
2. **Free notebook GPUs (Colab, Kaggle) cannot serve production traffic.** Their terms target interactive and research use, sessions are capped, and availability isn't guaranteed. They are good for development, model evaluation and batch experiments. Production GPU therefore has to come from free *credits* on a serverless GPU platform (Modal), which is legitimate but capped.
3. **A Spotify or YouTube link can identify a song but can't supply its audio.** Spotify removed `audio-features` and preview URLs for new apps (Nov 2024), and its developer terms forbid feeding its content into ML models. Downloading from YouTube or SoundCloud violates their terms. A pasted link therefore gives us the title and artist, and the musical data comes from open databases (§5 Stage 0). A **playlist** is several pasted links or a bundle of uploaded files.
4. **Quality of full-length club tracks from open models is unproven for our niche.** Phase 0 (§12) is a one-week spike to measure it before we build the product around any model.
5. **Truly $0 is achievable.** Optional real costs are a domain (~$10/yr; a free `*.pages.dev` subdomain works) and US DMCA agent registration ($6 every 3 years), which you need before a public launch with user uploads.
6. **The GPU is the only expensive resource.** Everything else fits in free tiers for the first ~1,000 users. Most of the design work therefore goes into spending fewer GPU-seconds: previews before full renders, quotas, caching, and early exits in the regeneration loop.

---

## 3. Technology stack

| Layer | Choice | Why | Free tier *(verify)* | Free fallback |
|---|---|---|---|---|
| Frontend | **Next.js (App Router) + TypeScript + Tailwind + shadcn/ui** | SSR for the landing and SEO pages, React ecosystem, easy to hire for later | — | Vite + React SPA |
| Waveform / player | **wavesurfer.js** | Waveform, regions (show sections), small | OSS (BSD-3) | Plain `<audio>` |
| Frontend hosting | **Cloudflare Pages/Workers** (via OpenNext) | Commercial use allowed on free plan, global CDN | Unlimited static requests; Workers ~100k req/day | Netlify free; Vercel Hobby is **non-commercial only** |
| Backend API | **FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic** | Async, OpenAPI generated automatically, same language as ML | — | — |
| API contract | OpenAPI → generated TS client (`openapi-typescript`) | One source of truth for types | — | — |
| Database | **Supabase Postgres** (+ `pgvector`) | Managed Postgres with vector search for embeddings | 500 MB DB, 2 projects, **pauses after 7 days idle** | Neon free; self-host Postgres on the Oracle VM |
| Auth | **Supabase Auth** (email magic link + Google/GitHub OAuth) | 50k MAU free, JWTs the API can verify locally via JWKS | 50k MAU | Self-hosted Authentik / Better Auth |
| Transactional email | **Resend** (custom SMTP in Supabase) | Supabase's built-in SMTP is heavily rate-limited | 3k/month, 100/day | Brevo free |
| Object storage | **Cloudflare R2** (S3 API) | **Zero egress fees**, presigned uploads, lifecycle rules | 10 GB-month, 1M writes, 10M reads | Backblaze B2 (10 GB) |
| Queue / workflow | **Postgres `jobs` table** with `FOR UPDATE SKIP LOCKED` | No extra infra; durable; workers anywhere pull via HTTPS | included | Hatchet (self-hosted, Postgres-based) when we outgrow it |
| AI framework | **PyTorch** + Hugging Face `transformers`/`diffusers`/`huggingface_hub` | What every candidate model ships on | — | — |
| Audio processing | **FFmpeg** (CLI), **librosa**, **pyloudnorm**, **soundfile**, **Demucs**, **Beat This!**, **LAION-CLAP**, **basic-pitch**, **Chromaprint (fpcalc)**, **AudioSeal** | See §5. All licenses allow commercial use; Essentia is AGPL, see §17. | OSS | — |
| Music models | **ACE-Step** (default), **Stable Audio Open 1.0 / Small**, MusicGen (dev only), YuE (later, vocals) | See §4.4 | OSS | — |
| API + CPU workers host | **Oracle Cloud Always Free** Ampere A1 VM, Docker Compose + Caddy (auto-TLS) | 4 OCPU / 24 GB RAM always-on is enough for API, analysis worker and CPU fallback generation | Always Free | Hugging Face Space (Docker, CPU basic 2 vCPU/16 GB, sleeps); Google Cloud Run free tier; Koyeb free |
| GPU (production) | **Modal** serverless GPU | Pay-per-second, scales to zero, free monthly credit, terms allow production | ~$30/month credit | Your own GPU PC as a pull worker |
| GPU (dev/eval) | **Kaggle** (~30 GPU-h/week), **Colab** free, local GPU | Model spikes, batch evaluations | free | Lightning AI free credits |
| CI/CD | **GitHub Actions** + GHCR | Unlimited minutes on a public repo, 2,000 min/month private | free | — |
| Errors | **Sentry** (Developer plan) | FastAPI + Next.js SDKs | ~5k errors/month | GlitchTip self-hosted |
| Product analytics | **PostHog** cloud | Funnels and feature flags in one | ~1M events/month | Umami self-hosted |
| Uptime | **UptimeRobot** / Better Stack | Alert when the free VM dies | 50 monitors | — |
| Logs/metrics | **Grafana Cloud** free | Loki + Prometheus hosted | generous free | `docker logs` 🙂 |

**Why a single Python backend:** analysis, prompting, scoring and generation adapters all live in one Python package with **optional dependency groups**. The API container installs only `[api]` (small, no torch). The CPU worker adds `[analysis]`, the GPU worker adds `[gpu]`. One codebase, three images.

### 3.1 Region plan (Philippines)

| Service | Region | Notes *(verify)* |
|---|---|---|
| Supabase | **Southeast Asia (Singapore)** | Region is fixed when the project is created |
| Oracle Cloud | **Singapore** as home region | The Always Free home region **can't be changed later**. Free ARM capacity in Singapore is often "out of host capacity", so retry at off-peak hours or start with a smaller shape (1–2 OCPU) and resize. Fallbacks: Tokyo, Osaka or Seoul, or the HF Space / Cloud Run options in §3. |
| Cloudflare R2 | Location hint **APAC** | Downloads go through Cloudflare's network, which has a Manila PoP |
| Cloudflare Pages | Global | — |
| Modal (GPU) | Default (any region) | Pinning a region is a paid feature. Generation is a background job lasting a minute or more, so extra latency to US GPUs doesn't matter. Only specs and generated audio leave the region. |
| Sentry / PostHog | US or EU cloud | No Asian region on free plans; they get no audio and only pseudonymous IDs |

Users outside Asia still get fast pages (Cloudflare CDN) and fast downloads (R2 through Cloudflare). Only API calls travel to Singapore.

### 3.2 Development machine
Your laptop (i5-12450H, 16 GB RAM, Intel UHD graphics, **no NVIDIA GPU**) with Docker Desktop on WSL2 can run everything **except** the large music models:
- Day-to-day development uses the **`fake` provider** (§11), which returns a synthetic click track instantly, so the whole app runs locally.
- Analysis (librosa, CLAP) runs fine on this CPU. Demucs is slow but usable on 30-second windows.
- Small models run on CPU for smoke tests: Stable Audio Open Small, and MusicGen-small (dev only).
- **Phase 0 and other model work run on Kaggle** (free, ~30 GPU-h/week) using the same pull-worker code as production. Production GPU is Modal.


**Home GPU PC (confirmed 2026-10-28):** AMD Ryzen 5 5600X (6 cores / 12 threads), **NVIDIA RTX 3060 with 12 GB VRAM**, 16 GB RAM, Windows 11 24H2 with Hyper-V virtualization enabled, stable internet, about 220 GB of free disk.

What it means for the plan:
- **Phase 0 runs at home** with no Kaggle hour limits. 12 GB fits Stable Audio Open, MusicGen and Demucs, and ACE-Step (with partial CPU offload if needed). Phase 0 measures the real speed; a rough guess is about a minute per 3-minute track.
- **It is the main GPU worker during the private beta**, with Modal as automatic fallback (§4.3). That saves Modal credits for the public launch.
- **No inbound ports:** the worker only makes outbound HTTPS calls to claim jobs, so there's no port forwarding and nothing on the home network is exposed.

Setup notes for Phase 0:
- Run the worker in **Docker Desktop with the WSL2 backend and GPU support**, the same image as Modal. After updating the NVIDIA driver, check that `nvidia-smi` works inside WSL2.
- WSL2 gets only half the RAM (8 GB) by default. Raise it to ~12 GB in `.wslconfig` so models can load with CPU offload. The 16 GB of system RAM is this PC's tightest resource.
- Budget ~60 GB of disk for model weights, Docker images and caches.
- Add a **pause switch** (stop the worker container) for gaming. The router then sends jobs to Modal automatically.
- **Power cost:** left idle all day, the PC uses roughly 50 kWh a month, about ₱600 at ~₱12/kWh *(verify your local rate)*. Each generated track costs only centavos. Run the worker while the PC is on anyway rather than keeping it on 24/7 for the app.
- **Brownouts:** if the PC goes offline mid-job, the job's lease expires and it is retried on Modal. Users only see a delay.

---

## 4. Software architecture

### 4.1 System diagram

```
                         ┌──────────────────────────────┐
  Browser ──────────────▶│  Web (Next.js, Cloudflare)   │
     │                   └──────────────┬───────────────┘
     │  presigned PUT/GET               │ HTTPS + Supabase JWT
     ▼                                  ▼
┌──────────┐            ┌─────────────────────────────────────────────┐
│ R2       │◀──presign──│  API (FastAPI)          [Oracle ARM VM]     │
│ uploads/ │            │   ├─ auth (JWKS verify), quotas, CRUD       │
│ outputs/ │            │   └─ Orchestrator (in-process module)       │
└──────────┘            │        ├─ pipeline state machine            │
     ▲                  │        ├─ provider registry + router        │
     │                  │        ├─ prompt builder / policies         │
     │                  │        └─ job dispatcher ──┐                │
     │                  └──────────────────────────┬─┼────────────────┘
     │                                             │ │
     │                         ┌───────────────────▼─▼───────────────┐
     │                         │ Supabase Postgres                   │
     │                         │  users · uploads · analyses ·       │
     │                         │  style_profiles · generations ·     │
     │                         │  outputs · jobs (queue) · pgvector  │
     │                         └───────────────────▲─────────────────┘
     │                                             │ (via API /internal)
     │        claim / heartbeat / complete         │
     │   ┌─────────────────────────────────────────┴──────────────────┐
     │   │                   Worker runtime (same code)               │
     │   │  ┌──────────────────┐ ┌──────────────────┐ ┌────────────┐  │
     └───┼──│ analysis worker  │ │ gen worker (GPU) │ │ gen worker │  │
         │  │ CPU, Oracle VM   │ │ Modal, on demand │ │ local GPU/ │  │
         │  │ ffmpeg, librosa, │ │ ACE-Step,        │ │ Kaggle     │  │
         │  │ CLAP, Demucs…    │ │ Stable Audio…    │ │ (dev/eval) │  │
         │  └──────────────────┘ └──────────────────┘ └────────────┘  │
         └────────────────────────────────────────────────────────────┘
```

### 4.2 Principles
1. **Nothing talks to a model except a provider adapter.** The API and frontend speak only in *style profiles* and *generation specs*.
2. **The orchestrator owns the pipeline. Workers execute single steps.** A worker never decides what happens next; it reports a result and the orchestrator advances the state machine. This keeps workers stateless and disposable, which suits free and preemptible compute.
3. **Workers pull and never receive pushes.** Free GPUs sit behind NAT and in notebooks. If every worker pulls jobs over HTTPS with a worker token, a Kaggle notebook, a home PC and a Modal container all join the same queue the same way. For Modal, the API simply *spawns* a container that then pulls.
4. **Everything is a durable job in Postgres.** If a worker dies, its heartbeat expires and the job is re-queued. No in-memory state matters.
5. **Version everything that affects output:** analyzer version, profile schema version, prompt template version, provider + model revision, seed. This gives reproducibility and lets us compare quality across versions.
6. **Monolith first.** The orchestrator is a Python module inside the API process, not a microservice. It can be split out later because it only communicates through the DB and job contracts.

### 4.3 The orchestrator

**Responsibilities**
- Run the per-generation **state machine** and enqueue the next job when one finishes.
- **Route** each generation to a provider/runtime based on capabilities, availability, user tier and budget.
- Apply **policies**: prompt sanitization, the similarity gate, regeneration limits, GPU budget per user and per day.
- Record **lineage** (which profile, prompt, seed and model produced which output).

**Generation state machine**

```
 QUEUED ─▶ PROMPTING ─▶ GENERATING ─▶ POSTPROCESSING ─▶ SCORING ─┬─▶ READY
                            ▲                                    │
                            └──── REGENERATING (new seed/prompt) ◀┤ score low / gate fail
                                                                 │  and attempts < max
                                                                 └─▶ FAILED / BLOCKED
```

Analysis has its own small machine per upload: `UPLOADED → VALIDATING → ANALYZING → ANALYZED | REJECTED | FAILED`, then `PURGED` once the raw audio is deleted.

**Provider interface (contract, not code)**

Each provider adapter declares a **capability manifest**:

| Field | Example (ACE-Step) | Used for |
|---|---|---|
| `id`, `model_revision` | `ace_step`, pinned HF commit | lineage, reproducibility |
| `license`, `commercial_ok` | Apache-2.0, true | router excludes `commercial_ok=false` in prod |
| `max_duration_s` | 240+ | routing, sectioned generation |
| `controls` | `tags`, `bpm_hint`, `seed`, `guidance`, `instrumental` | prompt builder knows which "dialect" to emit |
| `supports_extend` / `supports_inpaint` | true / true | preview→full-render, fixing bad sections |
| `audio_conditioning` | **disabled by policy** | the firewall: never pass reference audio |
| `runtime_requirements` | GPU ≥ 16 GB (or offload), ~X s per minute of audio | cost estimate, queue selection |
| `sample_rate`, `channels` | 44.1/48 kHz stereo | post-processing |

And exposes three operations: **`estimate(spec) → cost`**, **`generate(spec) → audio + metadata`**, **`health() → ok/degraded`**.

The **GenerationSpec** is the only thing a provider sees: target BPM, key/mode, duration, structure template (list of sections with bar counts and energy levels), genre/mood/instrument tags, the provider-specific prompt string, negative prompt, seed and guidance. Swapping or adding a model means writing one adapter plus one prompt dialect. Nothing upstream changes.

**Router policy (MVP):** default provider for the requested mode → if unhealthy or over budget, fall back to the next eligible provider (e.g. Stable Audio Open Small on CPU for short loops) → if none, queue with an honest ETA.

**Runtime preference (beta):** use the home GPU worker if it has sent a heartbeat in the last 2 minutes and the GPU queue wait is under ~3 minutes; otherwise spawn a Modal worker. Both run the same image and claim jobs the same way, so this is a dispatcher setting, not separate code.

### 4.4 Candidate models

| Model | License *(verify)* | Strengths | Weaknesses | Role |
|---|---|---|---|---|
| **ACE-Step** (3.5B, v1 or newer) | Apache-2.0 | Full songs of several minutes, fast (claimed ~20 s for 4 min on A100), tag-style prompts, instrumental mode, repaint/extend, LoRA fine-tuning | Training-data provenance not fully disclosed; club-genre fidelity unproven | **Default for full tracks** |
| **Stable Audio Open 1.0** | Stability AI Community License (free < $1M revenue) | Trained on CC-licensed Freesound/FMA audio (cleanest provenance), 44.1 kHz stereo, good drums and textures, BPM in prompt | Max ~47 s, weak long-form structure and melody | **Loops, one-shots, "clean-data mode"**, sectioned generation later |
| **Stable Audio Open Small** (~341M) | Same | Runs on CPU/ARM in seconds | ~11 s clips, lower quality | **CPU fallback**, instant previews |
| **MusicGen** small/medium/large | Code MIT, **weights CC-BY-NC** | Mature, well documented | **Not allowed commercially**; 30 s windows | Dev and eval baseline only |
| **YuE** | Apache-2.0 | Full songs with vocals from lyrics | Very heavy and slow; vocals out of scope | Post-MVP vocals experiment |

The Phase 0 spike chooses the default from measured results, not from this table.

### 4.5 Request flows

**Upload and analyze**
1. `POST /v1/uploads` → API checks quota, creates an `uploads` row, returns a presigned R2 PUT URL (size-limited, 15-min TTL).
2. The browser uploads directly to R2, so the API never carries audio bytes.
3. `POST /v1/uploads/{id}/complete` → orchestrator enqueues `analyze` (queue `cpu`).
4. The analysis worker claims the job, downloads from R2, runs the pipeline (§5), and posts the result.
5. The orchestrator stores `audio_analyses`, marks the upload `ANALYZED`, and schedules a **raw-audio purge** (default 24 h).

**Generate**
1. `POST /v1/generations` (with `Idempotency-Key`) → orchestrator debits quota, builds the spec + prompt, picks a provider, enqueues `generate` (queue `gpu`), spawns a Modal worker if none is warm.
2. GPU worker → audio to R2 → `postprocess` + `score` jobs (CPU) → READY or regenerate.
3. The frontend polls `GET /v1/generations/{id}` every 2–3 s (SSE later), then plays the preview MP3 via a short-lived presigned GET URL.

---

## 5. AI pipeline: analysis

All analysis runs on **CPU** on the Oracle VM. Long inputs (DJ mixes) are never analyzed end-to-end. They are **sampled**: N = 8–12 windows of 30 s spread across the file, each analyzed and then aggregated. This bounds CPU cost per upload regardless of mix length.

### Stage 0: Link resolution (no audio)

Links are handled by **link resolvers**: plugins that work like the music providers in §4.3. Each resolver declares which URLs it understands and returns the same small result: title, artist, ISRC if known, duration, and the song's IDs on other platforms. Adding a platform means adding one resolver; nothing else changes.

Resolvers are tried in this order:
1. **Platform-specific resolvers** for platforms with an official oEmbed endpoint or public API.
2. **Odesli (song.link) API.** One free call turns a link from any platform it supports into the same song's identity on the others *(verify rate limits and attribution terms)*.
3. **Open Graph fallback** for any other music site: read only the page's standard title tags.
4. **Manual:** if nothing works, the user types the song and artist name (MusicBrainz search).

| Platform | Resolver | Notes |
|---|---|---|
| Spotify, Apple Music, YouTube, YouTube Music, Deezer, Tidal, Amazon Music, Pandora, Audiomack, Boomplay, Anghami | Odesli (+ oEmbed where available) | The mainstream listening platforms; one integration covers them all |
| SoundCloud | oEmbed + Odesli | Home of many DJ edits and bootlegs |
| **Beatport**, Traxsource | Open Graph title → lookups below | The main club-music stores; important for DJs |
| Bandcamp | Open Graph title | Independent electronic artists |
| **Mixcloud** | Official oEmbed/API | DJ mixes. Its public tags (e.g. "tech house") feed the profile directly. |
| TikTok | Official oEmbed | Sound names are often "original sound – user", so the confirm step matters most here |
| Anything else | Open Graph → manual | Works whenever the page title names the song |

The MVP takes track links and Mixcloud mixes. Album and playlist links list their tracks where the platform's public data allows it; otherwise the user pastes tracks one by one. Each resolver's use of a platform must be checked against that platform's terms before launch *(verify)*.

Then, for every link:
1. **Clean the title:** strip noise like "(Official Video)", "[Lyrics]", "HD" or "Extended Mix" (the mix name is kept as a hint).
2. **The user confirms** "Is this the song?" with editable title and artist and the cover art. This catches mistakes, and the user can always just type the name.
3. **Look up musical data in open sources:**
   - **ISRC** (the song's international ID) from Odesli/Deezer where available, then **MusicBrainz by ISRC** for an exact match
   - **MusicBrainz** (CC0 data, 1 request/s): canonical recording, genres and tags
   - **GetSongBPM API** (free with a backlink *(verify)*): BPM and key
   - later, optionally, the **AcousticBrainz** data dump (CC0, frozen in 2022): BPM, key and danceability for millions of recordings, self-hosted.
4. **Fill the gaps** from the closest vibe preset. Energy arc, structure, groove and drums come from the preset that matches the genre, so link-based profiles are complete but coarser than upload-based ones.
5. Store the result as an `audio_analyses` row with `method = 'metadata'` and lower confidences. The rest of the pipeline is unchanged.

The song's title and artist **never** go into a generation prompt (§7 sanitizer); they are stored only so users can see their history. Lookups are cached by `(source, external_id)` and by ISRC, so a popular song is looked up once, even when users paste it from different platforms.

### Stage A: Ingest and validation
- `ffprobe`: real container/codec, duration, channels. Reject non-audio, files over 100 MB, over 20 min (MVP), and corrupt files.
- `ffmpeg` → 44.1 kHz stereo WAV (canonical) + 22.05 kHz mono (analysis).
- `sha256` of decoded PCM → **analysis cache key** (same file uploaded twice means analysis runs once).
- Loudness normalize the analysis copy (pyloudnorm) so features don't depend on mastering level.

### Stage B: Feature extractors
Each extractor is a pure function with a **version string**: `audio → feature + confidence`.

| Feature | Method | Library | Output |
|---|---|---|---|
| **BPM** | Beat/downbeat tracking; tempo from inter-beat intervals; resolve half/double-time with genre priors (house 118–128, techno 125–140, DnB 165–178…) | **Beat This!** (MIT) with a `librosa.beat` fallback | `bpm`, `confidence`, `beat_times`, `downbeat_times`, `tempo_stability` |
| **Key** | Beat-synchronous CQT chroma, correlated with key profiles. Use EDM-tuned profiles (Faraldo's EDMA) plus Krumhansl/Temperley and keep the best. | librosa + own ~50-line implementation | `key`, `mode`, `camelot`, `confidence`, top-3 |
| **Energy** | Per-bar RMS, LUFS (momentary), spectral centroid, onset density, low-end energy → combined, normalized 0–1 **energy curve** per 8 bars | librosa, pyloudnorm | `energy_mean`, `energy_curve[]`, `loudness_lufs`, `dynamic_range` |
| **Genre / mood / instruments** | **Zero-shot** CLAP: compare the audio embedding with text embeddings of a curated club taxonomy ("tech house track", "melodic techno", "amapiano log drum", "acid 303 bassline"…) | **LAION-CLAP** (music checkpoint) | tag → probability maps; 512-d **embedding** (stored in pgvector) |
| **Groove** | Onsets per band (low/mid/high) mapped onto the beat grid → **swing ratio** (16th off-beat delay), microtiming deviation, syncopation index, onset density per band | librosa + own logic | `swing`, `syncopation`, `density_by_band`, `microtiming_ms` |
| **Drum pattern** | Separate the drum stem → band-split onset detection (kick < 150 Hz, clap/snare transients 150 Hz–5 kHz, hats > 5 kHz) → quantize to a 16-step grid per bar → cluster bars → most frequent pattern(s) | **Demucs** htdemucs (MIT), librosa | e.g. `kick: x...x...x...x...`, `hat: ..x...x...x...x.`, `four_on_floor: true` |
| **Structure** | Beat-synchronous chroma + MFCC self-similarity → Foote novelty → boundaries snapped to 8/16-bar phrases → **club labels** from energy and drum presence (intro, groove, build, drop, breakdown, outro) | librosa | `sections[]: {label, start_bar, bars, energy}` |
| **Melody/bass contour** (internal only) | Pitch transcription of the bass/melody stems | **basic-pitch** (Apache-2.0) | Used **only** by the similarity gate (§8). Never sent to a generator. |

**MVP subset:** BPM, key, energy, genre/mood (CLAP), basic structure. **v1.1:** groove, drum pattern (Demucs is the slowest step, ~1–2× realtime on CPU for a 30 s window).

---

## 6. Style profiles

A style profile **aggregates one or more analyses** into a small, editable and versioned JSON document. It is the only artifact that crosses the firewall.

```
StyleProfile (schema_version 1)
├─ tempo:        { bpm: 124, range: [122, 126], swing: 0.56 }
├─ key:          { preferred: "A minor", camelot: "8A", alternatives: ["7A","9A"], lock: false }
├─ genre:        { "tech house": 0.62, "minimal": 0.21, "deep house": 0.11 }
├─ mood:         { "hypnotic": 0.7, "dark": 0.4, "euphoric": 0.1 }
├─ instruments:  ["punchy kick", "rolling bassline", "shuffled hats", "vocal chop", "stab chords"]
├─ energy:       { mean: 0.71, arc_template: [0.3,0.5,0.7,0.9,0.4,0.95,0.6,0.3] }   # per 16 bars
├─ structure:    [ {intro,32}, {groove,32}, {build,16}, {drop,32}, {breakdown,16}, {drop,32}, {outro,32} ]
├─ groove:       { syncopation: 0.38, density: {low:.5, mid:.6, high:.8} }
├─ drums:        { archetype: "four_on_floor_offbeat_hat", kick_pattern: "x...x...x...x..." }
├─ embedding:    centroid CLAP vector (internal, for scoring)
└─ provenance:   { source_analysis_ids: [...], weights: [...], analyzer_versions: {...} }
```

**Aggregation:** weighted median for scalars, weighted average of tag distributions (top-k kept), most-common key with alternatives, energy arcs resampled to a common length and averaged, and the medoid structure template. Users can **edit** every field in the UI ("make it darker", "lock to 126 BPM"). Edits are stored as overrides on top of the derived profile, so re-analysis doesn't wipe them.

Profiles are deliberately **coarse**. They describe a scene, not a song, which is what keeps outputs original.

**Vibe presets** use the same schema with `kind = 'preset'`. They are hand-written JSON files in `backend/src/pulseforge/presets/`, seeded into the database on deploy, and have no `provenance` sources. "Start from a preset, then tweak" creates a user-owned copy, so presets stay unchanged.

---

## 7. Prompt builder ("prompt enhancement" without a paid LLM)

**MVP: deterministic, template-based.** It is faster, free and testable, and good enough because the inputs are already structured.

1. **Spec composition:** profile + user controls (duration, energy slider, mood adjectives, "more/less" toggles) → `GenerationSpec`.
2. **Dialect rendering** per provider:
   - ACE-Step: comma-separated tags: `tech house, 124 bpm, A minor, punchy kick, rolling bassline, shuffled hats, hypnotic, dark, club mix, instrumental`, plus a section/structure hint where supported.
   - Stable Audio Open: a descriptive sentence with `BPM` and duration: `"Tech house loop, 124 BPM, punchy kick, rolling bassline, shuffled hats, dark hypnotic mood, club master"`.
   - MusicGen (dev): a natural-language description.
3. **Sanitizer (policy, mandatory):** strip artist names, song titles and labels from any user free text, using a blocklist built from the **MusicBrainz** artist dump (CC0) plus a "style of X" pattern rule. Rewrite "in the style of Artist" into genre and era descriptors, or reject it.
4. **Negative prompt** defaults: `vocals, singing, lo-fi, distorted, muffled, tempo change, silence`.
5. **Template versioning**: `prompt_template_version` is stored on each generation so A/B tests are possible.

**v1.1 (optional):** a small open LLM (e.g. Qwen2.5-3B-Instruct, Apache-2.0) running on CPU via `llama.cpp` on the Oracle VM. It turns free text ("something for 3am in a Berlin basement") into tag edits on the spec, **never directly into the model prompt**. Its output passes the same sanitizer.

---

## 8. Quality scoring, similarity gate and regeneration

### 8.1 Post-processing (before scoring)
FFmpeg/pyloudnorm chain:
1. Trim leading/trailing silence.
2. Gentle high-pass at 25 Hz, true-peak limiter.
3. Loudness: **−9 LUFS integrated / −1 dBTP** for the club master and **−14 LUFS** for the web preview.
4. Re-run BPM analysis. If drift is within ±3%, time-stretch to the exact target BPM. If tempo is unstable, flag it.
5. Apply the **DJ-ready treatment** (v1.1): confirm the first and last 16–32 bars are low-density and drum-led, otherwise fade-shape them or regenerate those sections with inpaint where the provider supports it.
6. **Watermark** with AudioSeal (MIT, inaudible), embed metadata (ID3/Vorbis: `AI-generated: PulseForge`, generation id) and plan C2PA manifests.
7. Encode: **MP3 192k preview** + **WAV 44.1 kHz/16-bit** (or FLAC) download.

### 8.2 Score (0–100, stored with a per-component breakdown)

| Component | Weight (initial) | How |
|---|---|---|
| Technical | 25% | clipping %, silence %, DC offset, spectral bandwidth (muffled detection), loudness range, codec-like artifacts (spectral flatness spikes) |
| Tempo adherence | 20% | abs(BPM − target), tempo stability across windows |
| Style adherence | 25% | CLAP cosine(output embedding, profile centroid) + CLAP text–audio similarity with the prompt + genre-tag agreement |
| Structure | 15% | detected section count/positions vs template, energy-curve correlation with the target arc |
| Key | 15% | key detected on output vs target (relative and fifth-related keys get partial credit) |

Weights are tuned later from user feedback (thumbs up/down, download = implicit positive).

### 8.3 Originality / similarity gate (hard gate, not weighted)
This runs on every output against **the user's reference analyses and their source audio while it still exists**, and later against a growing corpus of known tracks' fingerprints:
- **Chromaprint** fingerprint match → any match means **block**.
- **Melodic/bass contour** cross-similarity (basic-pitch notes, transposition-invariant, DTW) above a threshold → block.
- **CLAP embedding** cosine to a single reference above a threshold (e.g. > 0.92) → block. Matching the *centroid* closely is fine; it means "same vibe". Matching one track closely is suspicious.

Blocked outputs are never shown. They trigger a regeneration with a new seed and wider prompt variety, and are logged for threshold tuning.

### 8.4 Regeneration pipeline
- **Automatic:** if `score < 60` or the gate fails, and `attempts < 3` and the per-generation GPU budget remains → regenerate with an adjustment targeted at the failing component:
  - tempo off → strengthen BPM tokens, lower duration, or switch to a provider with explicit BPM control
  - style off → reweight the top-2 genre tags, add instrument tags
  - technical fail → new seed, lower guidance
  - gate fail → new seed, drop the most specific instrument/mood tags.
  Keep the **best-scoring** take if all attempts fail the soft threshold (never if it fails the gate).
- **User-initiated:** "Regenerate", "More like this" (same spec, new seed) and "Tweak" (edited spec). Each creates a **child generation** linked via `parent_generation_id`, so lineage forms a tree.
- **Preview-then-render (main GPU saver):** by default generate **2 × 30-second previews** with different seeds. The user picks one and only then renders the full 3–6 min track (using *extend* when the provider supports it; otherwise a re-render with the same seed and spec, which is similar but **not identical**, and the UI must say so).

---

## 9. Database schema (Postgres)

Supabase owns `auth.users`. Everything else lives in `public` and is **managed by Alembic migrations from the backend repo**, so there is one source of truth. RLS is enabled as defense in depth, but the frontend never queries tables directly; it goes through the API.

```
users_profile
  id uuid PK = auth.users.id
  display_name text
  plan text default 'free'                -- free | creator | pro (later)
  ui_mode text default 'simple'           -- simple | pro
  tos_version_accepted text, tos_accepted_at timestamptz
  created_at, updated_at

uploads
  id uuid PK, user_id uuid FK → users_profile
  kind text                               -- track | mix | bundle_item
  bundle_id uuid null                     -- groups files uploaded as a "playlist"
  storage_key text null                   -- null after purge
  original_filename text, mime text, size_bytes bigint
  duration_s real, pcm_sha256 text        -- cache key
  status text                             -- uploaded|validating|analyzing|analyzed|rejected|failed|purged
  rights_attested bool not null           -- user confirmed they may use this file
  purge_after timestamptz, purged_at timestamptz
  created_at
  INDEX (user_id, created_at desc), INDEX (pcm_sha256)

song_references                            -- pasted links (identity only, no audio)
  id uuid PK, user_id uuid FK
  source text                             -- resolver/platform id (spotify, apple_music, beatport, mixcloud…) or 'manual'
  url text, external_id text
  title text, artist text, isrc text null, musicbrainz_id text null
  platform_ids jsonb                      -- same song on other platforms (from Odesli)
  lookup jsonb                            -- raw open-database results
  created_at
  INDEX (source, external_id), INDEX (isrc)   -- lookup cache

audio_analyses
  id uuid PK
  upload_id uuid FK null, song_reference_id uuid FK null   -- exactly one is set
  method text                             -- audio | metadata
  pcm_sha256 text null
  analyzer_version text
  bpm real, bpm_confidence real, tempo_stability real
  key text, mode text, camelot text, key_confidence real
  loudness_lufs real, energy_mean real
  energy_curve jsonb, structure jsonb, groove jsonb, drums jsonb
  genre_tags jsonb, mood_tags jsonb, instrument_tags jsonb
  clap_embedding vector(512)
  contour_fingerprint bytea null          -- internal, for the similarity gate only
  chromaprint text null                   -- internal
  created_at
  UNIQUE (pcm_sha256, analyzer_version)   -- analysis cache

style_profiles
  id uuid PK, user_id uuid FK null        -- null for built-in presets
  kind text                               -- preset | user
  slug text null                          -- presets only, e.g. 'sunset-deep-house'
  name text, schema_version int
  derived jsonb                           -- computed from analyses
  overrides jsonb default '{}'            -- user edits
  centroid_embedding vector(512)
  created_at, updated_at, deleted_at

style_profile_sources
  style_profile_id uuid FK, analysis_id uuid FK, weight real
  PK (style_profile_id, analysis_id)

generations
  id uuid PK, user_id uuid FK, style_profile_id uuid FK
  parent_generation_id uuid null FK → generations   -- regeneration lineage
  mode text                               -- preview | full | loop
  use_case text                           -- dj_set | video | fun (Simple-mode picker)
  spec jsonb                              -- the full GenerationSpec (frozen)
  prompt_text text, negative_prompt text, prompt_template_version text
  provider text, model_revision text, seed bigint
  status text                             -- queued|prompting|generating|postprocessing|scoring|regenerating|ready|failed|blocked
  attempts int default 0, gpu_seconds real default 0
  error text null
  idempotency_key text null
  created_at, completed_at
  UNIQUE (user_id, idempotency_key)

generation_outputs                         -- every take, including discarded ones
  id uuid PK, generation_id uuid FK
  attempt int, seed bigint
  storage_key_master text, storage_key_preview text
  duration_s real, sample_rate int
  quality_score real, score_breakdown jsonb
  gate_passed bool, gate_details jsonb
  clap_embedding vector(512)
  watermark_payload text
  is_selected bool default false
  created_at

jobs                                       -- the queue
  id uuid PK, type text                   -- analyze|generate|postprocess|score|purge
  queue text                              -- cpu | gpu
  payload jsonb, result jsonb
  status text                             -- queued|running|succeeded|failed|dead
  priority int default 0, attempts int default 0, max_attempts int default 3
  run_after timestamptz default now()
  locked_by text, locked_at timestamptz, heartbeat_at timestamptz
  error text, created_at, finished_at
  INDEX (queue, status, priority desc, run_after) WHERE status='queued'

usage_ledger                               -- quotas / future billing
  id bigserial PK, user_id uuid FK
  kind text                               -- upload | analysis | preview | full_render | gpu_seconds
  amount real, generation_id uuid null, created_at

feedback
  id bigserial PK, user_id uuid FK, output_id uuid FK
  rating smallint                         -- -1 / +1
  reasons text[]                          -- 'off_tempo','boring','artifacts','not_my_style'…
  created_at

reports                                    -- copyright/abuse takedowns
  id uuid PK, reporter_email text, output_id uuid null, claim jsonb
  status text, created_at, resolved_at

workers                                    -- optional, for ops visibility
  id text PK, queues text[], capabilities jsonb, last_seen_at timestamptz
```

**Free-tier budget:** 500 MB holds hundreds of thousands of analysis rows. Embeddings (512 floats ≈ 2 KB) are the largest item, so store them only where scoring and search need them. Audio never goes in Postgres.

---

## 10. API design

REST + JSON, versioned under `/v1`, OpenAPI generated by FastAPI. Errors use **RFC 9457 `application/problem+json`**. Every mutating POST that costs money accepts an **`Idempotency-Key`** header. Auth is `Authorization: Bearer <Supabase JWT>`, verified locally against Supabase JWKS with no network round-trip.

### Public API

| Method & path | Purpose |
|---|---|
| `GET /v1/me` | Profile, plan, remaining quota |
| `POST /v1/me/tos` | Accept the current ToS version |
| `PATCH /v1/me` | Preferences, e.g. `ui_mode: simple\|pro` |
| `GET /v1/presets` | Built-in vibe presets (public, cacheable, no auth) |
| `DELETE /v1/me` | Account + data deletion (GDPR) |
| `POST /v1/uploads` | `{filename, size, mime, kind, bundle_id?, rights_attested}` → `{upload_id, put_url, expires_at}` |
| `POST /v1/uploads/{id}/complete` | Start validation + analysis → `202` |
| `GET /v1/uploads` / `GET /v1/uploads/{id}` | List / status |
| `DELETE /v1/uploads/{id}` | Delete upload, raw audio and analysis |
| `GET /v1/uploads/{id}/analysis` | Analysis summary (BPM, key, energy curve, tags, sections) |
| `POST /v1/links/resolve` | `{url}` → `{song_reference_id, title, artist, source}` for the user to confirm; no audio fetched |
| `POST /v1/links/{id}/confirm` | `{title?, artist?}` → open-database lookup → `{analysis_id}` |
| `POST /v1/style-profiles` | `{name, analysis_ids[], weights?}` or `{name, from_preset}` → derived profile (a copy when from a preset) |
| `GET /v1/style-profiles` / `{id}` | List / get (derived + overrides merged) |
| `PATCH /v1/style-profiles/{id}` | Update overrides |
| `DELETE /v1/style-profiles/{id}` | Soft delete |
| `POST /v1/prompts/preview` | `{style_profile_id, controls}` → `{spec, prompt_text, provider}`: dry run with no GPU, used for a "show me what you'll ask for" panel |
| `POST /v1/generations` | `{style_profile_id, controls, mode: preview\|full\|loop, use_case, variations: 1–2, from_output_id?}` → `202 {generation_id}` |
| `GET /v1/generations` / `{id}` | List / status + outputs with scores |
| `POST /v1/generations/{id}/regenerate` | `{spec_changes?, keep_seed?: bool}` → new child generation |
| `POST /v1/outputs/{id}/select` | Mark the chosen take (feeds preview→full render) |
| `GET /v1/outputs/{id}/stream` | `302` to a short-lived presigned URL for the MP3 preview |
| `GET /v1/outputs/{id}/download?format=wav\|mp3\|flac` | `302` to a presigned download URL; logs usage |
| `POST /v1/outputs/{id}/feedback` | `{rating, reasons[]}` |
| `POST /v1/reports` | Public takedown/abuse form (no auth, captcha via Cloudflare Turnstile, free) |

**Status updates:** MVP polls `GET /v1/generations/{id}` (cheap, and cacheable for 1 s). v1.1 adds SSE at `GET /v1/generations/{id}/events`.

### Internal worker API (`/internal`, worker token auth, not in the public OpenAPI)

| Method & path | Purpose |
|---|---|
| `POST /internal/jobs/claim` | `{worker_id, queues[], capabilities}` → one job or `204`, atomically locked with `SKIP LOCKED` |
| `POST /internal/jobs/{id}/heartbeat` | Extend the lease (every 15 s; lease expires at 60 s → re-queue) |
| `POST /internal/jobs/{id}/complete` | `{result}` → the orchestrator advances the state machine |
| `POST /internal/jobs/{id}/fail` | `{error, retryable}` → backoff retry or dead-letter |
| `POST /internal/storage/presign` | Presigned GET/PUT for the job's own objects only |

Workers never hold DB credentials, only a revocable worker token. A leaked Kaggle notebook token can then claim jobs at most; it can't read the database.

### Limits (free plan, MVP)
5 uploads/day, 20 min max each, 6 previews/day, 2 full renders/day, 3 auto-regenerations per generation. Enforced in the API from `usage_ledger` and surfaced in `/v1/me`.

---

## 11. Folder structure (monorepo)

```
pulseforge/
├─ apps/
│  └─ web/                         # Next.js (App Router)
│     ├─ app/                      # routes: (marketing), (app)/upload, profiles, studio, library
│     ├─ components/               # player/, waveform/, profile-editor/, ui/
│     ├─ lib/api/                  # generated OpenAPI client + fetch wrapper
│     └─ lib/auth/                 # Supabase client (auth only)
├─ backend/
│  ├─ pyproject.toml               # one package, optional extras: [api] [analysis] [gpu] [dev]
│  ├─ src/pulseforge/
│  │  ├─ api/                      # FastAPI app, routers/, deps (auth, quotas), errors
│  │  ├─ core/                     # settings, logging, db session, storage (R2) client
│  │  ├─ domain/                   # pydantic contracts: StyleProfile, GenerationSpec, AnalysisResult…
│  │  ├─ db/                       # SQLAlchemy models, repositories
│  │  ├─ orchestrator/             # state machines, dispatcher, router, policies, regeneration
│  │  ├─ queue/                    # jobs table claim/lease logic
│  │  ├─ analysis/                 # ingest.py, bpm.py, key.py, energy.py, tags_clap.py,
│  │  │                            # groove.py, drums.py, structure.py, aggregate.py
│  │  ├─ profiles/                 # profile aggregation + overrides merge
│  │  ├─ presets/                  # built-in vibe presets (hand-written JSON style profiles)
│  │  ├─ links/                    # link resolvers: base, registry, odesli/, mixcloud/, tiktok/, opengraph/, manual/
│  │  ├─ promptkit/                # spec builder, dialects/, sanitizer, blocklists
│  │  ├─ providers/                # base (capability manifest), registry,
│  │  │                            # ace_step/, stable_audio_open/, musicgen_dev/, fake/
│  │  ├─ postprocess/              # ffmpeg chain, loudness, time-stretch, watermark, encode
│  │  ├─ scoring/                  # technical, adherence, similarity gate
│  │  └─ worker/                   # generic worker runtime (claim → run → report)
│  ├─ migrations/                  # Alembic
│  └─ tests/                       # unit/ (pure functions), integration/ (db, queue), golden/ (audio fixtures)
├─ infra/
│  ├─ docker/                      # api.Dockerfile, worker-cpu.Dockerfile, worker-gpu.Dockerfile
│  ├─ compose.yml                  # local dev: postgres, minio (S3 stand-in), api, worker
│  ├─ compose.prod.yml             # Oracle VM: caddy, api, worker-cpu
│  ├─ modal/                       # Modal app definition for GPU workers
│  └─ notebooks/                   # Kaggle/Colab worker bootstrap (dev/eval only)
├─ eval/
│  ├─ prompts/                     # fixed benchmark specs (per genre)
│  ├─ references/                  # CC-licensed test audio only (FMA/Freesound) — never commercial tracks
│  └─ reports/                     # model comparison results (Phase 0 and onward)
├─ docs/
│  ├─ BLUEPRINT.md                 # this file
│  ├─ adr/                         # architecture decision records (one per major decision)
│  └─ legal/                       # ToS, privacy, DMCA policy drafts
├─ .github/workflows/              # ci.yml, deploy-web.yml, deploy-backend.yml, eval.yml (manual), codeql.yml
├─ LICENSE                         # AGPL-3.0
├─ SECURITY.md                     # how to report vulnerabilities privately
└─ CONTRIBUTING.md
```

Two notes. The **`providers/fake/`** adapter returns a synthetic click track instantly, so the whole product can be developed and tested end-to-end without a GPU. **`eval/references/`** holds only openly-licensed audio, so the test suite itself never depends on copyrighted music.

---

## 12. MVP scope and development milestones

Estimates assume one developer working **full-time**. Multiply by ~2.5 for evenings and weekends. Each milestone ends with something deployed.

| # | Milestone | Weeks | Scope | Done when |
|---|---|---|---|---|
| **0** | **Model & analysis spike** | 1 | Run ACE-Step, Stable Audio Open (+ MusicGen as baseline) on the home PC's RTX 3060 12 GB (plus one short Modal run to measure production cost) with 10 fixed club specs; run BPM/key/CLAP on 20 CC-licensed club tracks; measure seconds/minute-of-audio, VRAM, subjective quality (blind-rate yourself + 2 DJ friends) | `phase0/RESULTS.md` (kit in [phase0/](../phase0/README.md)) names a default provider and measured cost per track. **Go/no-go gate for the whole product idea.** |
| 1 | Foundations | 1 | Public monorepo (license, secret-scanning push protection, Dependabot, branch protection), CI (lint, types, tests), Supabase project, Alembic, auth in web + JWT verify in API, Oracle VM + Caddy + Cloudflare Pages deploys, Sentry | Sign up, log in, `GET /v1/me` works in production |
| 2 | Upload | 1 | Presigned R2 upload, validation via ffprobe, rights attestation, upload list, purge job, `jobs` queue + generic worker runtime | Upload a file and see it reach `ANALYZED` (with a stub analyzer) |
| 3 | Feature extraction + links | 2.5 | Ingest/transcode, BPM, key/Camelot, energy curve, CLAP tags + embedding, basic structure, mix sampling, analysis cache; link resolvers (Odesli, Mixcloud, TikTok, Open Graph, manual) + MusicBrainz/GetSongBPM lookups | Analysis page shows correct BPM/key on 18 of 20 eval tracks; links from Spotify, YouTube, Apple Music, SoundCloud, Beatport and Mixcloud each become a style profile |
| 4 | Presets, Simple mode, profiles, prompt builder | 2 | 8–10 hand-written vibe presets, Simple-mode wizard (vibe → use case → plain-language sliders), Pro-mode profile editor, aggregation, dialects, sanitizer, `/prompts/preview` | A new user with no uploads picks a preset and reaches "Generate" in under a minute; a Pro user builds a profile from 3 tracks and edits it |
| 5 | Generation | 2 | Provider interface + registry, ACE-Step adapter on Modal, fake provider, orchestrator state machine, quotas, post-processing (loudness, encode, watermark) | Click "Generate" and a playable preview arrives in under 2 min |
| 6 | Preview, scoring, download | 1 | Waveform player with sections, score + similarity gate, auto-regenerate (max 3), select → full render, WAV/MP3 download, feedback | End-to-end flow; blocked outputs never reach the UI |
| 7 | Beta hardening | 1 | Rate limits, ToS/Privacy/DMCA pages, takedown form, delete-my-data, uptime alerts, landing page, 20 invited beta users | Private beta live |

**Total ≈ 11.5 weeks to a private beta.** Presets need no analysis, so the preset half of M4 and all of M5 can move ahead of M3 if analysis runs late. A working "Generate" button early makes the better demo.

**Deliberately out of the MVP:** groove and drum-pattern extraction (v1.1), DJ-ready intro/outro treatment (v1.1), SSE, the LLM prompt helper, payments, stems, vocals.

---

## 13. Product roadmap

| Phase | Timeframe | Theme | Highlights |
|---|---|---|---|
| **MVP / private beta** | Months 0–3 | Prove the loop | §12. Success metric: ≥30% of beta users download a track they rate 👍. |
| **v1.1** | Months 3–4 | DJ-ready | Groove + drum extraction feeding the spec, exact-BPM correction, 32-bar mixable intros/outros, Camelot-aware generation ("give me something that mixes out of 8A"), SSE |
| **v1.2 Public launch** | Months 4–6 | Monetize to fund GPU | Paid "Creator" tier via **Lemon Squeezy / Paddle** (merchant of record handles VAT; no monthly fee, percentage per sale; both pay out to Philippine sellers *(verify)*). Stripe doesn't accept Philippine-based businesses. For local buyers, add **PayMongo** (GCash, Maya, local cards). Free tier stays with lower quotas. Stems (Demucs on outputs), MIDI export of bass/lead (basic-pitch). **Remix mode** for owned or licensed uploads (§1.6). |
| **v2** | Months 6–12 | Own the sound | **LoRA fine-tunes of ACE-Step on licensed/CC club data** (per-genre LoRAs), sectioned arrangement editor (regenerate just the breakdown), style-profile sharing/marketplace, producer API |
| **v3** | Year 2+ | Platform | Own model trained on licensed catalog deals, real-time/live performance tools, DAW plugin (VST via JUCE), label-partner "official style packs" |

---

## 14. Deployment strategy

### Environments
- **Local:** `docker compose` with Postgres, MinIO as an R2 stand-in, the API, the CPU worker and the `fake` provider. Optionally a local GPU worker. No cloud accounts are needed to develop. This runs on your current laptop through Docker Desktop (WSL2).
- **Staging:** second free Supabase project, `staging` R2 bucket prefix, the same Oracle VM under a different compose project/port, Cloudflare preview deployments for every PR.
- **Production:** Supabase prod project, R2 prod bucket, Oracle VM, Modal app `pulseforge-prod`, Cloudflare Pages production branch.

### Pipelines (GitHub Actions)
1. **`ci.yml` on every PR:** Ruff + mypy/pyright + pytest (unit + integration against a Postgres service container); ESLint + `tsc` + Vitest for web; OpenAPI client regeneration with a diff check (fails if types drift); Docker build check.
2. **`deploy-web.yml`:** Cloudflare's Git integration builds previews per PR and production on `main`.
3. **`deploy-backend.yml` on `main`:** build the multi-arch images (`linux/arm64` for Oracle, `linux/amd64` for Modal) → push to GHCR → SSH to the VM → `alembic upgrade head` → `docker compose pull && up -d` (rolling restart; Caddy health-checks) → `modal deploy` for GPU worker changes.
4. **`eval.yml` (manual dispatch):** run the fixed benchmark specs against a provider and commit the report. This is how model upgrades get approved.

### Practices
- **Migrations:** only additive changes deploy without coordination. Destructive changes use expand → migrate → contract across two deploys.
- **Secrets:** GitHub Actions secrets + `.env` on the VM (root-only, 0600). Modal secrets in Modal. Nothing in the repo.
- **Public repo hygiene:** turn on GitHub secret scanning with push protection, Dependabot and CodeQL (all free for public repos), and run `gitleaks` in CI. Protect `main` with a branch rule. Deploy workflows run only on pushes to `main`, through a protected GitHub Environment. They never run on pull requests from forks, and `pull_request_target` is never used. Values that would help abusers, such as similarity-gate thresholds, rate limits and extra blocklist entries, live in server config rather than in the repo.
- **Rollback:** images tagged by git SHA; roll back with `IMAGE_TAG=<sha> docker compose up -d`.
- **Backups:** the Supabase free tier has **no** downloadable automated backups. Run a nightly `pg_dump` from the VM to R2 (encrypted with `age`), keep 14 days.
- **Keep-alive:** a daily cron touches Supabase (free projects pause after 7 idle days) and the Oracle VM keeps CPU above the idle-reclaim threshold *(verify Oracle's current idle-instance policy)*.

---

## 15. Scaling strategy

The binding constraint is GPU-seconds. Everything else is cheap.

| Stage | Users | What breaks | Response |
|---|---|---|---|
| **A: Beta** | 0–100 | Modal credits; home PC availability | Home RTX 3060 as the main GPU worker with automatic Modal fallback; quotas (§10), previews before full render, analysis cache by hash, fake provider in dev |
| **B: Early growth** | 100–1k | Credits exhausted around mid-month | Launch a paid tier whose price is above GPU cost per user; CPU fallback (Stable Audio Open Small) for loops; **priority queues** (paid users first); batch several previews per container warm-up |
| **C: Traction** | 1k–10k | Single VM CPU for analysis, queue contention, cold starts | Move API to Cloud Run / Fly with autoscaling; analysis workers scale on queue depth; keep a minimum of 1 GPU warm at peak hours; consider RunPod/Vast.ai spot GPUs as extra pull workers (the pull model makes this easy); Supabase Pro ($25/mo) for backups and no pausing |
| **D: Scale** | 10k+ | GPU cost dominates P&L | Dedicated reserved GPUs; distilled/quantized model variants; caching common style-profile "bases"; own fine-tuned model; multi-region R2 is already global |

### Unit economics (to be filled from the Phase 0 measurements)
`cost_per_full_track ≈ (gpu_seconds_per_track × $/gpu_second) × avg_attempts + cold_start_overhead`

For planning only: if a 3-min ACE-Step render takes ~60 GPU-s on an A10G-class GPU at ~$1.10/h, the cost is **≈ $0.02 per attempt**, and $30/month of credit then covers roughly 1,000–1,500 tracks including retries and previews. **Replace these numbers with measured ones in Phase 0.**

Design choices that keep scaling cheap: direct-to-R2 uploads and downloads (API bandwidth stays tiny), stateless workers, a DB-backed queue that can later move to Hatchet/Redis with no API change (the claim/complete protocol stays), and the provider abstraction (a cheaper model can be swapped in per tier).

---

## 16. Cost sheet

| Item | Monthly cost | Notes |
|---|---|---|
| Cloudflare Pages + R2 | $0 | Watch R2 storage: purge raw uploads after 24 h, expire free-tier outputs after 30 days |
| Supabase | $0 | Pauses when idle; 500 MB |
| Oracle Always Free VM | $0 | Card required at signup for verification |
| Modal | $0 up to the monthly credit | Hard spending limit = credit amount; set a budget alert |
| GitHub, Sentry, PostHog, Resend, UptimeRobot, Grafana Cloud | $0 | Free tiers |
| Domain | ~$1/mo (≈ $10/yr) | **Optional**: `pulseforge.pages.dev` is free |
| DMCA designated agent | $6 per 3 years | **Needed** before public launch in the US with user uploads |
| Home PC electricity | ~₱0–600 | Only the extra hours the PC stays on for the app (§3.2) |
| DTI business name (Philippines) | One-time ₱200–₱2,000 depending on scope *(verify)* | Only when you start charging or operating as a business |
| BIR registration (Philippines) | No annual registration fee since 2024 *(verify)*; bookkeeping is on you | Needed once you earn revenue |
| **Total** | **$0–$1** | Before revenue |

**Paid upgrades, in the order they'll be worth it:** (1) more GPU when credits run out; the paid tier must pay for it. (2) Supabase Pro ($25) for backups and no pausing, once real users depend on it. (3) A lawyer review of the ToS before paid launch (see §17).

---

## 17. Legal and copyright

*This is an engineering plan, not legal advice. Get a lawyer to review it before the paid launch. Law school IP clinics and startup programs often do this for free.*

### 17.1 Model and library licenses (a hard gate in code)
- The provider manifest carries `license` and `commercial_ok`. **Production config refuses to route to `commercial_ok=false`**, so MusicGen can never accidentally ship.
- Do not use: **MusicGen/AudioCraft weights** (CC-BY-NC), **MERT** (CC-BY-NC), most **Essentia** pre-trained models (CC-BY-NC-SA). Essentia itself is **AGPL-3.0**. Because PulseForge is public under AGPL-3.0, its algorithms (e.g. key detection with EDM key profiles) are usable, but its pre-trained models stay non-commercial. **madmom model files** are non-commercial; prefer Beat This!.
- Keep a `docs/legal/THIRD_PARTY.md` listing each dependency, version, license and the date it was checked.

### 17.2 Training-data provenance
Major labels sued Suno and Udio in 2024 over training data and have since moved toward licensing settlements. Our models' training data is our inherited risk:
- **Stable Audio Open** was trained on CC-licensed audio, giving the cleanest provenance. Offer it as **"Clean mode"** (and as the default for B2B/content-creator users who need certainty).
- **ACE-Step/YuE** have less-documented data. Disclose which model made each track (stored in lineage), and be ready to switch the default if the legal landscape moves. The provider abstraction is what makes that switch cheap.
- Long-term (v2+): fine-tune only on **licensed or CC-licensed** club data.

### 17.3 Input side (user uploads)
- **Links:** the app never downloads audio from streaming services. Links only identify a song (§5 Stage 0).
- **Rights attestation** checkbox per upload and in the ToS.
- **Uploads are processed, not kept:** raw audio is deleted after analysis (default 24 h; the user can delete immediately). Only derived features remain, and tempo, key, genre and energy are not copyrightable expression.
- Uploads are **never shared, never played back publicly and never used for training** without separate opt-in consent.

### 17.4 Output side (what we generate)
- **The firewall ("Inspired by" mode):** no audio conditioning, melody conditioning or continuation from uploaded audio. Generators only see coarse style specs.
- **Remix mode (v1.2)** deliberately keeps parts of the uploaded audio, so the firewall doesn't apply there. Instead it relies on a rights confirmation per file, private-by-default labeling and the takedown process. Where a licensed fingerprint lookup is available, it also blocks remixes of known commercial releases (AcoustID needs a paid agreement for commercial use *(verify)*).
- **Similarity gate** (§8.3) on every output; blocked outputs are logged and never delivered.
- **Prompt sanitizer:** no artist names, song titles or "in the style of <artist>".
- **No vocals in the MVP**, which removes voice-likeness and right-of-publicity risk.
- **Labeling:** inaudible watermark (AudioSeal) + metadata marking the track as AI-generated. This supports transparency obligations such as the **EU AI Act Art. 50** marking of synthetic content *(verify current application dates and guidance)*, and the AI-disclosure fields that distributors increasingly require.

### 17.5 Ownership and ToS
- The US Copyright Office's position (2025 report) is that **purely AI-generated material is not copyrightable**; human creative contribution may be. The ToS must therefore **not promise exclusive ownership**. It should grant users whatever rights PulseForge holds, with a broad license to use the output commercially, and state that outputs may resemble other works by chance.
- The ToS must also cover: acceptable use, a repeat-infringer policy, a takedown process, liability limits, minimum age (16+ to keep GDPR simple), and governing law.

### 17.6 Platform obligations
- **DMCA safe harbor (US):** register a designated agent ($6), publish the takedown procedure (`/v1/reports` + email), act quickly, and terminate repeat infringers.
- **Privacy (GDPR/CCPA):** collect minimal PII (email only), provide a privacy policy, `DELETE /v1/me` for full deletion, and list sub-processors (Supabase, Cloudflare, Modal, Resend, Sentry, PostHog). Data stays in Singapore where possible (§3.1).
- **Distribution platforms:** Spotify and others have policies against impersonation and spam. Tell users to disclose AI use when distributing.

### 17.7 Philippines-specific
- **Data Privacy Act of 2012 (RA 10173)**, enforced by the **National Privacy Commission (NPC)**. PulseForge is the personal information controller, so it needs a privacy notice with a lawful basis (consent or contract), a designated **Data Protection Officer** (the founder can be the DPO), reasonable security measures, and **breach notification to the NPC and affected users within 72 hours**. Registering with the NPC is required only above thresholds, such as 250+ employees or sensitive personal information of 1,000+ people *(verify the current NPC circular)*. PulseForge collects only email and usage data, so it should stay below them. Using Singapore and US sub-processors is allowed, but you remain accountable, so list them in the privacy notice.
- **Intellectual Property Code (RA 8293, as amended)** governs copyright locally. It has no exact equivalent of the DMCA safe harbor, so the notice-and-takedown process in §17.6 is still the right behavior. Keep the **US DMCA agent** registration because users will come from the US too.
- **Minors:** keep the 16+ minimum age.
- **Low-cost advice:** IPOPHL and university Innovation and Technology Support Offices (ITSOs) are starting points for IP questions before paying a lawyer.
- **Business registration** (DTI, then BIR) happens before you charge money; see §16.

---

## 18. Security and abuse

- **Upload hardening:** size cap enforced by the presigned URL's content-length, audio is decoded only inside the worker with FFmpeg (CPU/time limits via `ulimit`/timeout), files are never executed or served from the API origin, and object keys are random UUIDs.
- **AuthZ:** every query is scoped by `user_id` from the verified JWT, with RLS as a second line.
- **Workers:** revocable token per worker, limited to `/internal`, with presign scoped to the job's own object keys.
- **Abuse:** per-user + per-IP rate limits (in-app token bucket in Postgres; Cloudflare's free WAF rules in front), Turnstile on signup and reports, disposable-email blocklist (free tier farming is the main abuse vector for a GPU product).
- **Secrets:** never logged, nothing secret in the frontend except the Supabase anon key (which is designed to be public).

---

## 19. Observability

- **Structured JSON logs** with `request_id`, `user_id`, `generation_id` and `job_id` flowing API → job payload → worker.
- **Metrics:** queue depth and wait time per queue, job duration per type, GPU-seconds per generation, attempts per generation, gate block rate, score distribution, and the conversion funnel (upload → profile → preview → full render → download).
- **Ops dashboard:** a simple admin page in the app (it reads the `jobs`, `generations` and `workers` tables) before Grafana is needed.
- **Alerts:** VM down, queue wait > 10 min, job failure rate > 10%, Modal spend at 80% of credit.

---

## 20. Risks and open decisions

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Open models' club-music quality is not good enough | Medium | **Fatal** | Phase 0 go/no-go; LoRA fine-tune path; pivot to "loops & stems" (Stable Audio Open's strength) if full tracks disappoint |
| Free GPU credits shrink or disappear | Medium | High | Pull-worker design accepts any GPU source; CPU fallback; paid tier |
| Oracle reclaims the free VM | Low–Med | Medium | Everything in compose + nightly backup; redeploy to HF Space / Cloud Run in < 1 h (documented runbook) |
| Legal landscape shifts on training data | Medium | High | Clean mode, provider swap, provenance lineage per output |
| Abuse of the free tier | High | Medium | Quotas, Turnstile, email verification, IP limits |
| Scope creep (solo developer) | High | High | MVP list in §12 is the contract; everything else goes to the roadmap |

**Decisions made (2026-10-28):**
1. **Audience:** everyone, with beginners first, served by Simple mode and Pro mode (§1.2–1.3).
2. **Repo:** public at [github.com/joseterdes/pulseforge](https://github.com/joseterdes/pulseforge), licensed **AGPL-3.0**. Anyone can read and self-host the code, but a company that runs a modified version as a service must publish its changes. It's owned by the founder's personal account, and commits use GitHub's private noreply email. `main` is protected: changes go through pull requests with CI (lint, Phase 0 smoke test, gitleaks).
3. **Region:** Singapore, the closest to the Philippines (§3.1).
4. **GPU:** the laptop has no NVIDIA GPU. The home PC's **RTX 3060 12 GB** runs Phase 0 and is the main GPU worker during the beta, with Modal as automatic fallback (§3.2, §4.3).
5. **Song input:** users paste a link from any major platform (Spotify, YouTube, Apple Music, SoundCloud, Deezer, Tidal, Beatport, Mixcloud, TikTok and more, via pluggable link resolvers), or upload audio. A link only identifies the song. The default result is an original track "inspired by" it; true remixes come in v1.2, for owned or licensed uploads only (§1.6).

**Still open:**
- Oracle home region: try Singapore first. If no free ARM capacity turns up after a few days, pick Tokyo or Osaka; the choice is permanent.
- Check the name "PulseForge" for trademark conflicts (IPOPHL and USPTO searches are free) before buying a domain or marketing.

---

## 21. Future improvements

- **Fine-tuning:** per-genre LoRAs on ACE-Step trained on licensed/CC data, and preference tuning (DPO-style) from 👍/👎 feedback.
- **Arrangement engine:** section-by-section generation with inpainting, so a user can say "regenerate only the breakdown" or "extend the drop by 16 bars".
- **Stems and MIDI:** Demucs separation of outputs plus basic-pitch MIDI, for producers to finish tracks in their DAW.
- **DJ integrations:** export with cue points and beat grid for Rekordbox/Serato/Traktor; "mixes-out-of" generation (match key and BPM to the next track in a set).
- **Style profile library:** share and remix community profiles, which also works as a growth loop.
- **Evaluation harness:** automated FAD and CLAP-score benchmarks per release, and human blind tests with beta DJs.
- **Real-time and live:** low-latency loop generation for live sets (Stable Audio Open Small class models).
- **Vocals (carefully):** licensed or consented voice models only, built on YuE-class models.
- **Producer API** and a DAW plugin.
- **Licensed data partnerships** with labels and sample-pack companies, leading to an owned model.
