# Phase 14C — long-form rough cut and quality tracker (2026-11-24)

Base: Phase 14B 476d3f7cc7566a153f7b5be41ac899d12f125453, CI run 45445134977 passed. Same draft PR #7; main stays Phase 13. No owner data, account access, database migration or publishing authorization.

## Actual evidence

- Original 932-word English SHA-256 lesson, 8 chapters, 24 planned visual beats. References: NIST Secure Hash Standard, Python hashlib, Microsoft Get-FileHash and NIST digital signatures. Source references are not independent claim verification.
- Native 1920x1080/30fps H.264/AAC, both stream durations 375.800s; full FFmpeg decode succeeded. Linux render + decode 62.23s. Actual 125 of 256 differing bits for the exact UTF-8 bytes hello and Hello. No continuous camera animation: progressive boards and cuts, with three equally time-divided visual beats per scene; semantic shot synchronization pending.
- Rough-cut SHA256 138f6d56ed388b198fa02cfa62a257848ff2ce19769afcc6c9dc9379bacd366d; plan SHA256 eb5a7ef2df3f371cad4b9c51d8275df5f6e3bf0ee59f8b28f6e8f5b7318c1e54. Original programmatic boards and synthetic eSpeak English narration only.
- Existing Phase 14B mastering module processed the full film: before -20.93 LUFS/-1.29 dBTP; after -16.74 LUFS/-1.40 dBTP, LRA 1.7 LU, gain +4.93dB. First candidate passes internal -16 +/-1 LUFS and <= -1 dBTP; full decode passed. Mastered SHA256 1583f1f665b041df3224599d355796bea994c71cc5154978d76a6cf7799a8b17. Human listening and licensed natural narration still required. Not professional certification.
- Scene transcript WebVTT (whole paragraphs, not publishable subtitles); chapter timing JSON; 1280x720 thumbnail board draft (watermarked, not a final YouTube thumbnail or CTR evidence).
- 12/12 isolated portable tests passed; all three new source/test/plan Git blobs match local files. Local full checkout remains DNS-blocked; latest integrated CI, release manifest refresh, owner Windows, actual native browser review, and Phase 13 queue integration pending.

## Reproduce

Use trusted local Python, Pillow, FFmpeg/ffprobe (libx264/AAC), eSpeak and a local TrueType font. No downloads initiated. Create an existing private parent directory; choose a fresh nonexistent output path. The tool is specific to this SHA-256 draft and supports ASCII English only; not a generic autonomous director. Failed runs retain INCOMPLETE; large intermediate WAV/PNG files are retained for review. Never put owner media or licenses into the public Git repository.

    python -m tools.phase14_film --plan tools/phase14_film_plan.json --output /private/phase14c-rough --font /path/to/DejaVuSans.ttf
    python -m tools.phase14_quality master /private/phase14c-rough/rough_cut.mp4 /private/phase14c-mastered --sha256 <exact-rough-cut-hash>
    python -m pytest -q tests/test_phase14_film.py

## Consolidated acceptance tracker

| Priority | Gate | Status / remaining proof |
|---|---|---|
| P0 | Natural English + Hindi narration | BLOCKED_OWNER_MODEL_OR_RECORDING; licensed models or recorded WAVs, native-speaker audition and pronunciation review |
| P0 | Story / research | ORIGINAL_ENGLISH_DRAFT; 932 words / 8 chapters; factual, pacing and native Hindi adaptation review pending |
| P0 | Motion graphics | FULL_HD_ROUGH_CUT; 24 progressive compositions; continuous motion, shot-specific layouts and semantic timing pending |
| P0 | Captions | SCENE_TRANSCRIPT_ONLY; Phase 14B reviewed-word engine not integrated with this film; actual acoustic alignment and readability review |
| P0 | Audio mastering | LONG_FORM_NUMERIC_PASS; licensed voice, listening review, final mix required |
| P1 | Packaging | DRAFT_TITLE_AND_WATERMARKED_BOARD; designed final thumbnail and truthful title approval pending |
| P1 | Long-form video | TECHNICAL_ROUGH_CUT_375.8S; professional bilingual editorial film pending |
| P1 | Rights and editorial | BLOCKED_HUMAN_REVIEW; independent source, rights, originality, full watch-through |
| P1 | Existing private review integration | OPEN; do not bypass synthetic-demo restrictions or owner authorization |
| P2 | Resource optimization | HOST_BENCHMARK_62.23S; actual Windows device cost, latency and revisions unknown |
| Phase 13 | Physical Windows / browser / recovery | OPEN; owner execution and evidence needed |
| M3.2 | Real private YouTube upload | BLOCKED_OWNER_AUTHORIZATION; no upload/publish or live Analytics tested |
| Recovery | 13–20 Nov source history | BLOCKED_OWNER_BACKUP |
| Release | Integration and package | OPEN; full integrated tests, manifest refresh, review and explicit merge needed |

Next: improve actual motion and scene timing, obtain licensed bilingual narration and align words, then integrate the approved film into the existing private review queue. No public publishing, GPU inference, revenue or 12-domain acceptance claimed. See [project status](PROJECT_STATUS.md).
