# ViralOS — Phase 14C creative quality review branch

**Current review checkpoint (2026-11-24):** original eight-chapter, 932-word English SHA-256 technical rough cut (375.8s, 1080p/30fps, full decode passed). Long-form numeric audio gate passed (-16.74 LUFS, -1.40 dBTP). Synthetic eSpeak English narration, progressive boards and scene transcript only; no publication authorization. Main remains Phase 13.

Start with the [consolidated project status](docs/PROJECT_STATUS.md) and [Phase 14C priority tracker and reproduction guide](docs/PRIORITY_TRACKER_2026-11-24_PHASE14C.md). Review [Phase 14A](docs/PHASE14_CREATIVE_DIRECTOR_AND_TRACKER_2026-11-24.md) and [Phase 14B](docs/PHASE14B_QUALITY_TRACKER_2026-11-24.md). Existing Phase 13 installation documentation follows unchanged.

---

# ViralOS — Phase 13: production-readiness candidate

Start with the [Windows setup and pilot guide](docs/PHASE13_DEPLOYMENT_AND_PILOT_2026-11-24.md). Assisted setup and pilot launch wrappers require trusted Python 3.12, FFmpeg and owner approval for dependency installation. One source-linked technical pilot is rendered and queued for review; no publishing permission. See [exit gates](docs/PRIORITY_TRACKER_2026-11-24_PHASE13.md).

---

# ViralOS — Phase 12: local editorial browser console

Opt-in loopback-only browser interface for configured drafts, fresh technical audit, verified MP4 bytes, scene checklist submission and durable review history. No arbitrary path API or publishing permission. See [operator guide](docs/PHASE12_LOCAL_REVIEW_CONSOLE_2026-11-24.md) and [remaining gates](docs/PRIORITY_TRACKER_2026-11-24_PHASE12.md).

---

# ViralOS — Phase 11: durable private editorial review queue

Offline SQLite review queue with fresh media audits, immutable draft pins, transactional review revisions, duplicate/stale submission rejection, and privacy-minimized history. Synthetic demos remain blocked; the queue never authorizes publication. See [operator guide](docs/PHASE11_DURABLE_REVIEW_QUEUE_2026-11-24.md) and [remaining gates](docs/PRIORITY_TRACKER_2026-11-24_PHASE11.md).

---

# ViralOS — Phase 10: editorial review handoff

Offline hash-bound review packets and per-scene source, narration, visual, rights, originality and caption self-attestations. Synthetic demos cannot complete the editorial checklist; no publication permission or independent reviewer verification is implied. See [operator guide](docs/PHASE10_DOMAIN_EDITORIAL_HANDOFF_2026-11-24.md) and [remaining gates](docs/PRIORITY_TRACKER_2026-11-24_PHASE10.md).

---

# ViralOS — Phase 9: independent domain draft media audit

Phase 9 fixes short-scene AAC truncation and adds a local pinned-manifest auditor that reconstructs narration and captions and checks sampled decoded audio/visual conformance. **No publishing permission, factual clearance or professional voice acceptance is implied.** See [Phase 9 operator guide](docs/PHASE9_DRAFT_MEDIA_AUDIT_2026-11-24.md) and [remaining gates](docs/PRIORITY_TRACKER_2026-11-24_PHASE9.md).

---

# ViralOS — Phase 6: offline narration-in-render integrity & localhost browser boundary

The bilingual owner-delivery audit now compares decoded MP4 audio with each **hash-bound, reviewed source WAV** using bounded correlation, and fails closed if audio is absent or inconsistent. AAC/mixing may cause false negatives: **this does not recognize speech, certify a speaker, prove every word, or replace human listening**. The local-only FastAPI UI also rejects DNS-rebound Host headers and foreign browser Origin/Fetch-Metadata requests. These are safety controls, not a password/authentication system against local malware.

See [Phase 6 implementation and test limits](docs/PHASE6_MEDIA_AUDIO_AND_LOCALHOST_SECURITY_2026-11-24.md) and [remaining engineering gates](docs/PRIORITY_TRACKER_2026-11-24_PHASE6.md). No external YouTube upload or voice-model download was performed. The suspended GitHub account remains untouched.

---

# ViralOS — 24 November 2026 Phase 5: owner-only acceptance evidence

**Active repository:** `mohdazizshaikh/youtube`, not the suspended former account. Phase 5 adds **offline** voice listening self-attestation, bilingual original-video artifact inspection, and read-only PRIVATE YouTube Studio evidence linkage, plus strict SRT timing and exact voice-to-reviewed-script checks. These are **technical operator gates, not independent proof of real human review, voice licensing, live OAuth, or permission to upload**. Source records, licenses, models, reviewer notes and account secrets must remain outside Git and outside any public report.

Read [Phase 5 owner instructions](docs/PHASE5_OWNER_AUDIO_BILINGUAL.md), [acceptance evidence guide](docs/PHASE5_EVIDENCE_AND_LIMITATIONS_2026-11-24.md) and [updated priority tracker](docs/PRIORITY_TRACKER_2026-11-24_PHASE5.md). Run `python -m pytest -q` and `python tools/verify_package.py` after extraction.

---

# ViralOS — 24 November 2026 Phase 3: CTC provenance, timing benchmark & no-duplicate upload recovery

**New repo only:** `mohdazizshaikh/youtube`; older suspended account never accessed. This is an incremental engineering checkpoint built on 634-file Phase 2. Real voice/acoustic models, owner Windows machine and owner YouTube OAuth are **NOT provided**; no live publishing, automatic Hindi/English dubbing or GPU inference is claimed.

New offline-only code: verify SHA-256 and explicit owner-rights declarations for **every local CTC model file** before optional inference; measure real/reference word alignment *when owner supplies both sets of timestamps*; reconcile a `REMOTE_UNKNOWN` PRIVATE upload only after exact read-only owner-channel verification plus Studio confirmation (never re-upload); harden backup ZIP extraction against unsafe Windows device/ADS paths. Additive SQLite migration `013`, without modifying older SQL.

Read [M2.4 model and benchmark guide](docs/M24_CTC_PROVENANCE_AND_BENCHMARK.md), [M3.2 remote-unknown recovery](docs/M32_REMOTE_UNKNOWN_RECOVERY.md) and [Phase 3 engineering gates](docs/PHASE3_ENGINEERING_GATES_2026-11-24.md).

---

# ViralOS — 24 November 2026 Phase 2: Offline Production Safety & Localized CPU Preview

**Safe destination:** `mohdazizshaikh/youtube` only; no operations involving the old suspended GitHub account. **Owner real-account, licensed models and target Windows PC still NOT accepted.**

New: *real CPU-rendered* multilingual technical MP4 preview from a human-reviewed localized script, owner-attested WAV, exact matching localized on-screen headings and owner-timed captions; SQLite migration `012`. **Not automatic TTS/dubbing or publication.** PRIVATE YouTube upload execution now requires a *current M2.6 editorial signoff*, even with OAuth and opt-in enabled. Isolated no-network backup/restore drills, Windows owner-run acceptance harness, Windows CI contract job, and a 24-video twelve-domain acceptance matrix are included.

Read [Phase 2 engineering evidence](docs/ENGINEERING_GATES_2026-11-24_PHASE2.md), [Phase 2 remaining-work tracker](docs/PRIORITY_TRACKER_2026-11-24_PHASE2.md), and [24-domain-video acceptance matrix](docs/DOMAIN_24_VIDEO_RELEASE_MATRIX.json). These are bounded tested increments, **not** complete professional voices, 12 full autonomous domain systems, real YouTube uploads, or licensed GPU video generation.

---

# ViralOS — 24 November 2026 Offline Engineering Update

**New repo only:** `mohdazizshaikh/youtube`. The suspended previous account was never contacted.

New code adds **12 domain-specific research metadata adapters**, **human-reviewed Hindi/English/Hinglish localization records**, an **independent source/media/editorial checklist**, **offline owner-backup reconciliation**, **GPU model routing contract (dry-run only)** and **observational retention-to-scene mapping**. See [November 24 Engineering Gates](docs/ENGINEERING_GATES_2026-11-24.md), [priority tracker](docs/PRIORITY_TRACKER_2026-11-24.md) and [changelog](CHANGELOG.md).

**Not production-complete:** no full natural voice or translation system, no real local GPU generation, no live YouTube private upload or owner-Windows validation, no demonstrated 144 runnable AI experts. The additional review layers do not bypass existing source, rights, voice, final-render or upload approval gates. A locally declared Analytics source is not independently authenticated.

---

# ViralOS M2.4 / M3.2 / M4 Engineering Increment — 23 November 2026

**Status:** Implemented and locally tested code increment, **NOT** live-account/production acceptance. The repository was recovered from archived sources without accessing the suspended former account. Original releases remain in `recovery/original-artifacts/`.

- [M2.4 offline Hindi/English CTC alignment + owner review, M3.2 read-only private YouTube verification and Windows acceptance instructions](docs/M24_M32_ENGINEERING_HANDOFF.md)
- [Exact completed, planned and blocked work](docs/PRIORITY_TRACKER_2026-11-23.md)
- M2.4 backend: `app/m24_audio.py`, `app/m24_routes.py`, `sql/009_m24_alignment.sql`, optional `tools/m24_align_local.py` and `tools/m24_voice_preflight.py`; **no pretrained model included**.
- M3.2 read-only owner tool: `tools/m32_private_acceptance.py`. It cannot upload or publish video and requires separate owner OAuth on the owner's machine.
- Windows read-only preflight `tools/windows_acceptance.ps1`; local-only verified SQLite/outputs backup `tools/offline_backup_restore.py`.
- `python -m pytest -q` and `python tools/verify_package.py` check the new package. `BUILD_REPORT.json` is retained as an older historical checkpoint; new evidence in `ENGINEERING_REPORT_2026-11-23.json`.

---

# ViralOS Launch M0–M3 + M2.2 / M3 Private Upload v0.5

This ZIP contains **runnable Python/FastAPI application code** plus the canonical Launch v3 specification snapshot, Windows scripts, optional research and narration connectors, a diagnostic dashboard, SQL migrations, private export workflow and tests.

**This is an honest engineering checkpoint, not a complete AI autopublisher or professional video studio.** The exact capabilities, limitations, Windows instructions and opt-in Google Analytics setup are in [docs/IMPLEMENTATION_M1_M3.md](docs/IMPLEMENTATION_M1_M3.md).

Quick start (Windows, Python 3.12, FFmpeg installed):

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\start_windows.ps1
```

Open http://127.0.0.1:8000 . Python API docs: http://127.0.0.1:8000/docs .

Modules: `app/main.py` legacy working M0 workflow; `app/expansion.py` new M1/M2/M3 endpoints; `app/intelligence.py` bounded feed/claim/timeline logic; `app/source_connectors.py` explicit approved RSS fetch; `app/tts.py` optional Piper; `app/youtube_analytics.py` optional read-only OAuth/Analytics; `app/renderer.py` original CPU technical render. `sql/004_m1_m3.sql` contains additive durable records.

**Legacy upload and all PUBLIC publishing are disabled.** A new M3 PRIVATE-only upload adapter is available after a separate human final-video review, verified account OAuth, and opt-in. No actual live upload has been tested. M2 Studio PREVIEW renders are watermarked and cannot be sent. Users must not treat an owner-attested claim or downloaded RSS title as independently verified.

## M2 CPU Studio v0.3 — new in this checkpoint

The old working M0–M3 endpoints, scripts and schema are retained. The new `app/studio_contracts.py`, `app/studio_routes.py` and `app/studio_render.py` provide an **actual CPU-rendered overlay/timeline studio prototype**, SQL migration `005_studio.sql`, rights-attested owner assets, owner-timed captions, WAV duration guard and QC manifest. The dashboard contains the **M2 Studio Director** panel.

Read [docs/M2_STUDIO_IMPLEMENTATION.md](docs/M2_STUDIO_IMPLEMENTATION.md) and [docs/STATUS_M2.md](docs/STATUS_M2.md). Technical video previews remain **NOT PUBLISH READY**. No automatic web footage ingestion, dubbing, GPU generation or uploads are enabled.

## M2.1 Creative Director + voice timing — new

The `M2.1 Automatic Creative Draft` panel now generates a first editable **deterministic script-based** HOOK → EXPLANATION → PAYOFF scene plan, with no generated sports facts. Upload narration WAV clips for each sentence/scene, or optionally synthesize locally with a licensed and matching-language Piper installation. The system measures individual WAV durations, composes an immutable per-plan voice track and produces **measured segment-level (not word-level)** caption timing. It also accepts owner-reviewed target-locale scripts, with locale-specific visuals/text and separate voice assets. A measured scene-boundary SRT is downloadable, and only unambiguous existing script claim links are transferred (not independently verified). Rendering is still CPU/Pillow/FFmpeg and not publish ready.

**Full instructions:** [docs/M2_1_DIRECTOR_IMPLEMENTATION.md](docs/M2_1_DIRECTOR_IMPLEMENTATION.md) and [docs/STATUS_M2_1.md](docs/STATUS_M2_1.md).

**Optional Piper configuration** on Windows PowerShell before starting the app:

```powershell
$env:VIRALOS_PIPER_EXE = "C:\path\to\piper.exe"
$env:VIRALOS_PIPER_MODEL = "C:\path\to\licensed-voice.onnx"
$env:VIRALOS_PIPER_MODEL_RIGHTS_OK = "1"
$env:VIRALOS_PIPER_LOCALE = "en-US" # MUST match the project's Director draft
```

No model is bundled or downloaded automatically. The app will refuse synthesis if the model, license attestation or locale is absent. Tests include a mocked Piper adapter, not a live installed model test.

`sql/006_m21_director.sql` is additive to all previous databases (001–005 migrations retained). The full test suite now includes director, locale, source isolation, audio hash and real-render tests. Run `python -m pytest -q` and `python tools/verify_package.py` after extraction. This is development software, not yet tested on the target Windows PC.

## M2.2 and M3 owner-reviewed final-video path (new)

Read **[docs/M2_2_AND_M3_PRIVATE_IMPLEMENTATION.md](docs/M2_2_AND_M3_PRIVATE_IMPLEMENTATION.md)**. This update adds source/shot creative QA, original CPU tactical-motion graphics, per-word **owner-reviewed timestamp** VTT import (NOT automated alignment), human-approved final video exports, and optional strictly PRIVATE YouTube upload with separate OAuth desktop CLI. Default upload state OFF. Existing source/evidence research, video studio and read-only analytics remain intact.

Run `python -m pytest -q`, then `python tools/verify_package.py`. Production approval, copyrighted footage clearance and YouTube monetization are **not** guaranteed.

## Phase 4 operator-only Piper/scene retiming

See `docs/PHASE4_PIPER_AND_SCENE_RETIME_2026-11-24.md` for the new licensed local Piper voice draft CLI and owner-verified scene retiming route. No voice model is bundled; synthetic test audio is not natural speech, and no publish action is automatically authorized.

## Phase 7: source-linked specialist storyboard drafts

Use `python -m tools.domain_storyboard --demo-all --animatics --output-dir outputs/domain-demo-v1` for 24 synthetic domain/format draft pairs. See [Phase 7 operator guide](docs/PHASE7_DOMAIN_STORYBOARDS_2026-11-24.md). The diagrams are illustrative, the MP4s are silent three-second previews, and none is accepted for publication.

## Phase 8: narrated domain draft composition

See [Phase 8 operator guide](docs/PHASE8_NARRATED_DOMAIN_DRAFTS_2026-11-24.md). Use `python -m tools.domain_draft_demo --output-dir outputs/narrated-demo-v1` for 24 synthetic English two-scene drafts, or `python -m tools.domain_draft_video` with local hashed WAV assets and a plan. These are watermarked nonpublication drafts, not complete accepted films.
