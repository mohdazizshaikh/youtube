# Phase 14A — Professional content quality and creative director (2026-11-24)

Base: Phase 13 e01f1b7e6e40f61cd2ed3553b0daa923a7a04cc5. Separate review branch. No DB migration, changes to earlier release gates, YouTube access, network downloads, or publication authority. Main remains the Phase 13 candidate until review. This is a standalone technical preview, not an integration with Phase 13's reviewed delivery pipeline.

## Reproduce locally

Prerequisites: trusted Python with Pillow, FFmpeg/ffprobe with libx264/AAC, eSpeak and a local TrueType font. No bundled model or font. Use an absent output directory with an existing parent; never use production media paths.

    python -m tools.phase14_preview --output /private/phase14-preview --font /path/to/DejaVuSans.ttf
    python -m pytest -q tests/test_phase14_preview.py

A failed run leaves INCOMPLETE. A complete one writes preview.mp4, captions.vtt and receipt.json. Use a fresh directory for retries. The rendering subprocess timeout is bounded at wait and CLI calls, but streamed input does not have an independent watchdog. This tool is for trusted local use only.

## Executed evidence

Linux standalone rendering: 4 scenes, 800x450, 24 fps, H.264/AAC, 33.501 seconds. Video fully decoded by FFmpeg; hash verified; calculated 125/256 changed bits for literal UTF-8 hello vs Hello. Frame clock, no-overwrite and nonrelease assertions verified. Two-pass audio V2: -17.07 LUFS integrated, -1.82 dBTP, 7.26 seconds elapsed on test host. Internal target -16 +/-1 LU, maximum -1 dBTP; **audio_target_pass=false**. SHA-256: ec8cf1a6a270dd70ab9b8e44639c312221e845efe9c6435738df266f784f1635. No owner PC speed estimate. Separate WebVTT is scene-level, not acoustically word-aligned or optimized for reading speed. Original programmatically generated visuals, no external music/footage. The existing Phase 13 references are retained, not independently re-reviewed. Synthetic narration is intentionally marked. Hindi text is a draft translation, not dubbed or native-reviewed.

## Priority tracker

| Priority | Gate | Status and next evidence |
|---|---|---|
| P0 | Hindi and English natural narration | BLOCKED: rights-verified owner model or recorded WAV, native speaker audition, latency and pronunciation. Reuse Phase 4 Piper and M2.4 provenance. |
| P0 | Storytelling and direction | PARTIAL: hook, experiment, reveal, practical caveat; review pacing and source claims, then 6–8 minute original script. |
| P0 | Motion | PARTIAL: real animated data reveal; 1080p, differentiated compositions, transitions, safe areas, integration and visual audit needed. |
| P0 | Animated captions | OPEN: existing scene WebVTT only; actual CTC/manual ground-truth words, bilingual line breaking, timed highlight and rendered-media review. |
| P0 | Mastering | FAIL: -17.07 LUFS vs -16 +/-1; adjust dynamics, remeasure encoded audio, listen on headphones and phone. |
| P1 | Thumbnail/title | OPEN: candidate title 'One Character Changes Everything: SHA-256 Explained'; no performance claim. Review visual accuracy, truthful title, thumbnail readability. |
| P1 | Original long-form | OPEN: first one-channel 6–8 minute SHA-256 practical lesson; not a padded short. |
| P1 | Editorial/rights | BLOCKED: independent full bilingual watch-through and evidence; existing private review gate unchanged. |
| P2 | Cost/time | PARTIAL: host elapsed 7.26s, no real cost or Windows measurement; record end-to-end revision time and owner costs. |
| Phase 13 | Windows, browser, rollback, authorized PRIVATE upload | OPEN; prior gates remain authoritative, no synthetic preview may be uploaded. |
| Recovery | 13–20 November unavailable source history | BLOCKED_OWNER_BACKUP. |

## Release criteria

Only after licensed human-approved narration, word alignment benchmark (proposed median <=80ms, p95 <=200ms against reviewed reference; not a measured result), integrated loudness/peak pass, 1080p 16:9 render, captions and full native-speaker editorial/rights review, actual Windows/browser acceptance, and existing owner-authorized PRIVATE export gate. No autonomous public publish. A successful render or green CI alone is insufficient. Stop adding domains until one bilingual pilot passes.

Full repository checkout was unavailable in the test container (DNS); only standalone local validation performed. Review exact code, run existing full regression/package manifest checks and Phase 13 integration before merging. This branch does not update the existing package manifest; a fresh manifest is required for release packaging.
