# ViralOS — YouTube Automation Platform

**Recovery repository, rebuilt on 2026-11-23 from locally available historical archives.** This is the independent new source location for the project. **No access was made to the suspended former GitHub account.** This repository is NOT claimed to contain that remote's unavailable most-recent commit history.

## Source checkpoint

- Application root is the preserved **ViralOS Launch M2.2 + M3 private, v0.5** source archive from **2026-11-12**: FastAPI, SQLite migrations 001–008, tests, dashboard, research/story/CPU media prototypes, rights-review/final-export and opt-in private-only YouTube adapter.
- The original source README is preserved at [`docs/history/README_M2_2_M3_original.md`](docs/history/README_M2_2_M3_original.md).
- Canonical design snapshots: [`spec/ViralOS_Launch_v3/`](spec/ViralOS_Launch_v3/) (from source ZIP), [`spec/ViralOS_Combined_v3/`](spec/ViralOS_Combined_v3/) (separate latest available Combined v3).
- Full 12-domain/144-engine *specified* inventory and historical AI handoff: [`handoff/`](handoff/). Registry != production engine completion.
- Prior archives, screenshots, demo footage and source snapshots are retained byte-for-byte under [`recovery/original-artifacts/`](recovery/original-artifacts/) with SHA-256 inventory. They are **historical artifacts**, not automatically-executed scripts.
- No live YouTube OAuth upload, private real-account analytics, target Windows i7 machine acceptance, natural quality multilingual TTS or GPU operation is claimed verified.

## Getting started (CPU-first, Windows)

Install Python 3.12 and FFmpeg/FFprobe; use:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\start_windows.ps1
```

Dashboard runs on `http://127.0.0.1:8000` (localhost only), and API docs at `/docs`. See `docs/IMPLEMENTATION_M1_M3.md`, `docs/STATUS_M2_2_M3.md` and historical source README for setup, security constraints and steps.

Development tests from the archived checkpoint (re-run in your environment):

```bash
python -m pytest -q
python tools/verify_package.py
node --check app/static/app.js
```

No real YouTube publishing should be enabled without owner review and a new explicit authorization. The only network publishing adapter is **PRIVATE-only, opt-in, supervised**. Never treat historical test counts as proof of live acceptance.

## Current project tracking

Read [`recovery/RECOVERY_STATUS.md`](recovery/RECOVERY_STATUS.md) and [`recovery/PROVENANCE_MANIFEST.json`](recovery/PROVENANCE_MANIFEST.json) before any new engineering. **Do not silently claim missing Nov 13–20 commits were recovered.** Use code/test-level evidence for every implementation claim.

## Safety

Never commit OAuth credentials, refresh tokens, license-restricted media, private personal data or `.env` files. Repository is PUBLIC. Asset-rights attestations in source are not legal clearances.
