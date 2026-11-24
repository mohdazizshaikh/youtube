# Phase 14I — Hindi localization, owner speech intake and bilingual packaging (2026-11-25)

Base f8892ef23b2da3f687d2fdfa25f9a65609c2c2ea; [Phase 14H CI run 45462466461](https://github.com/mohdazizshaikh/youtube/actions/runs/45462466461) passed. Continue draft PR #7; main stays Phase 13. No production DB changes, external model downloads, account access, real CTC inference or upload/publication permission.

## Executed workstreams

- Original 772 whitespace-token Hindi adaptation draft with eight chapters/24 narration segments, localized chapter titles and beats. Source-plan SHA declaration points to original Phase 14C English plan; the adaptation is shorter and is not independently translated, claim-reviewed, or certified equivalent. Hindi plan SHA256 eaf1eefbe8b4ff920297a3adc9a2c289fdfe9adacd6e7f67dad69237d89042a9. Source reference declaration is not an independent verification of translation or facts.
- Local eSpeak Hindi synthesized all 24 segments; converted to mono PCM16/48kHz. Intake validates exact ordered filenames, per-segment script SHA256, WAV SHA256, 1–90s nonzero PCM and padding, recalculates localized timeline rather than using English duration. Manifest SHA256 5b982404944060fc7efc1acd4548c49f90e69dd9104c75ae71d51dd3445153e1; assembled WAV SHA256 65482c237d3a75a76cb0f949d1232813ed171119e326cdd61245d716c3ea84be, 9829 frames, 327.633333s (5m27.63s). Hindi draft does not meet prior English 6–8 minute target; duration and pacing need native review. Nonzero sample check is not voice recognition or listening QC. Source is synthetic, not natural/licensed voice acceptance.
- Generated all 24 1920x1080 static boards with Pillow RAQM and local FreeSans/DejaVu Sans fonts, text-width checks, visibly shaped mixed Hindi/Latin sample; actual chapter-one preview with three static boards and PCM-driven cuts, 43.6s/1308 frames, 1920x1080/30fps H.264/AAC, full decode passed. Preview SHA256 b34d2ee16ee2d9fbe8e805403487fd28b51fb7780dc14858fc2b4fb9a86dead1. No full Hindi MP4, word captions, mastering gate or scene-specific cinematic motion claim. Human watch-through and font portability pending.
- Owner request kit writes 24 exact UTF-8 scripts and an intentionally invalid manifest template with null WAV hashes and false declarations. Supports owner-reviewed recording/local TTS WAV intake in Hindi; rights/listening references are declarations only. No professional TTS backend/model inference, owner recordings, English full-film replacement workflow or acoustic alignment verified. Private licensed model/recording and independent reference annotation remain prerequisites.
- Bilingual packaging module uses actual SHA256 bitwise XOR for hello/Hello (125 of 256 differing bits). Two original 1280x720 private draft PNGs, English title/description and eight timestamped chapters bound to V6 video/timeline; Hindi metadata bound to draft plan, no claimed Hindi video hash/chapter timestamps. English thumbnail SHA256 25d147b683e76e351d0977ff978a3c76974d1e99250d8a11cb08dec24ce0f554; Hindi thumbnail SHA256 6f4640b51be0f7516591ad9875f467114e323a07c0547215937acd30e0a65833. Metadata SHA256 0638c22e177c1c4c927ff6738bcfd0c9a9206d0def879da45a7f13a2c81bed7f. Both review-only watermarks; no CTR or publication approval.
- 18/18 isolated regression tests passed (plan order, PCM retime, unsafe names, hash mismatch, incomplete declarations, invalid/truncated/silent WAV, owner request fail-closed and bit experiment). Four source/plan/test Git blobs matched local bytes. Full local repo checkout previously DNS-blocked; latest integrated CI/manifest verification pending. Actual browser playback, physical Windows and owner account acceptance not performed.

## Reproduce and owner handoff

Use trusted Python/Pillow with RAQM support, local mixed-script font with Hindi/Latin coverage, local eSpeak and FFmpeg/ffprobe. No fonts/models bundled or downloaded. Choose fresh private directories outside source tree and do not commit speech assets or rights records. Failed runs may retain INCOMPLETE. Use trusted owner-controlled paths; symlink file rejection is not a sandbox for hostile shared storage.

    python -m tools.phase14_localize request --plan tools/phase14_hi_plan.json --output /private/owner-voice-kit
    python -m tools.phase14_localize fixture --plan tools/phase14_hi_plan.json --output /private/hi-fixture
    python -m tools.phase14_localize prepare --plan tools/phase14_hi_plan.json --manifest /private/hi-fixture/manifest.json --assets /private/hi-fixture/assets --output /private/hi-prepared --fontpath /local/mixed-script-font.ttf --latinfont /local/latin-font.ttf
    python -m tools.phase14_localize preview --prepared /private/hi-prepared --chapter 1 --output /private/hi-preview
    python -m tools.phase14_packaging --hi-plan tools/phase14_hi_plan.json --video /private/v6/polished_review.mp4 --receipt /private/v6/receipt.json --timeline /private/motion/receipt.json --output /private/packaging --fontpath /local/mixed-script-font.ttf --latinfont /local/latin-font.ttf
    python -m pytest -q tests/test_phase14_localize.py

Owner workflow: review Hindi script with native speaker, obtain licensed local voice or original recordings, record each exact script as assets/NN.wav (mono PCM16 48kHz), compute actual hashes, complete a new manifest only after reviewing rights/listening and use prepare. No credentials or private speech required in Git. Independently annotate representative real words and run actual licensed local alignment model before using Phase 14H benchmark. Target median <=80ms and nearest-rank p95 <=200ms; no synthetic evidence closes this gate. Obtain complete scene/word-caption review before any export. On Windows follow Phase 13 trusted setup and use local fonts, verify RAQM available, run acceptance, local review UI and restore test; retain actual logs. No Windows acceptance claim.

## Priorities

| Priority | Gate | Status / next proof |
|---|---|---|
| P0 | CI/package | Phase 14H green; Phase 14I manifest refresh and latest CI pending |
| P0 | Hindi localization | 8 chapters, 772-word draft; actual native-language/factual review, pacing and full film pending |
| P0 | Hindi voice | 24 synthetic segments and owner WAV intake tested; BLOCKED_OWNER_MODEL_OR_RECORDING for natural voice |
| P0 | English voice | Existing synthetic full film; full-film owner voice replacement and licensed model/recording pending |
| P0 | Acoustic alignment | Phase 14H arithmetic evaluator ready; actual inference/independent annotations pending |
| P0 | Captions | English synthetic only; actual English/Hindi word alignment and native playback needed |
| P0 | Creative | Hindi 24 static boards and 43.6s chapter preview; differentiated motion and full localized render pending |
| P0 | Audio | English V6 numeric pass; Hindi mastering, natural speech and human listening pending |
| P1 | Packaging | Two bilingual draft thumbnails and metadata generated; actual human review, Hindi video/chapter binding pending |
| P1 | Editorial | Separate Phase 14 API workspace tested previously; physical browser and complete human review pending |
| P1 | Windows/recovery | BLOCKED_OWNER_HARDWARE; actual install, browser playback/seek, restore and resource logs |
| P1 | YouTube | BLOCKED_OWNER_AUTHORIZATION; no live upload/analytics |
| P2 | Resource optimization | Actual owner device CPU/RAM/time/cost unmeasured |
| Recovery | 13–20 Nov source history | BLOCKED_OWNER_BACKUP |
| Release | Merge | OPEN; latest CI, reviewed integration and owner acceptance; main preserved |

Next parallel batch: actual owner bilingual voice assets and real alignment if available; full localized render, verified captions and mastering; native review/packaging and owner Windows/browser evidence; preserve private review restrictions. Do not expand across 12 domains or approve synthetic content. See [project status](PROJECT_STATUS.md).
