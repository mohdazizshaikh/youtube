# Phase 14B — verified mastering and reviewed word-caption preparation

2026-11-24. Continues Phase 14A draft PR #7; no changes to main, database, release authorization, existing owner review gates, or account access. Phase 14A CI run 45438729656 succeeded. Full local repository checkout is still unavailable (DNS); the new module and tests were tested in isolation and their Git blobs matched the local bytes.

## Executed results

- Actual Phase 14A V2 input SHA256 ec8cf1a6a270dd70ab9b8e44639c312221e845efe9c6435738df266f784f1635. Before: -17.07 LUFS, -1.82 dBTP. Separate experimental +1.1dB trial measured -16.22 LUFS/-1.43 dBTP.
- Reusable module applied measured correction +1.07dB and oversampled limiter, encoded once from V2, then measured the final AAC. V3: -16.24 LUFS, -1.37 dBTP, 1.7 LU LRA; first candidate passes internal -16 +/-1 LUFS and <=-1 dBTP. Full FFmpeg decode passed. Output SHA256 4315d53a552339f9c2d31c44971064ac023c212951eadff6740763012edba51f. Container duration 33.519s, original video 800x450/24fps, not a native full-HD pilot. Audio generation loss and listening quality still require review; no professional mastering certification.
- Local pytest: 12/12 passed (caption generation, no overwrite, nine invalid input cases, numeric thresholds and bad source hash). No live model inference.
- Actual libass burn-in of a four-second silent synthetic bilingual timing fixture at 1920x1080/30fps decoded successfully. Sample at 1.5s visibly shows the second Hindi word highlighted, with Hindi/English glyphs rendered using host font fallback. This is not evidence of actual alignment, font portability, or 1080p cinematic pilot quality.

## Usage

Trusted local inputs only; FFmpeg with loudnorm, alimiter, AAC and libass for burn-in; local fonts with correct script coverage. No model or font downloads. Keep private files and review manifests out of Git. Output paths must not exist; create the parent first. Failed runs retain INCOMPLETE. Mastering may fail if no bounded candidate passes. Inspect and retain private failure evidence; retry in a new path.

    python -m tools.phase14_quality master /private/preview.mp4 /private/mastered --sha256 <exact-source-hash>
    python -m tools.phase14_quality captions /private/script.txt /private/voice.wav /private/words.json /private/captions
    python -m pytest -q tests/test_phase14_quality.py

Words JSON example (replace placeholders with exact file hashes, and timestamps with actual owner-reviewed timing):
    {"locale":"hi-IN","basis":"owner_reviewed_manual","wav_sha256":"<hash>","script_sha256":"<hash>","words":[{"text":"नमस्ते","start_ms":120,"end_ms":620}]}

Script must contain exactly the supplied whitespace-delimited words, including punctuation. PCM16 mono/stereo 8–48kHz, <=10min, nonoverlapping integer millisecond boundaries, minimum 40ms per word. ASS quantizes to centiseconds and highlights one word within a four-token group, with gaps blank. No automatic acoustic alignment, semantic segmentation, full subtitle readability certification or rights/identity verification. Even an owner_reviewed_ctc label is only a declaration. Rendered output must undergo native-speaker review and matching existing M2.4 benchmark. Do not treat this module as a replacement for editorial gates.

## Remaining gates

| Priority | Status |
|---|---|
| P0 natural Hindi/English voices | BLOCKED_OWNER_MODEL_OR_RECORDING; exact licensed WAV, native audition and true alignment needed |
| P0 storytelling | PARTIAL; develop original 6–8min source-reviewed lesson |
| P0 motion graphics | PARTIAL; four animated 800x450 scenes; native full-HD differentiated compositions not yet implemented |
| P0 animated captions | PARTIAL; real synthetic burn-in, reviewed input contract; true speech alignment and pilot integration pending |
| P0 mastering | NUMERIC_PILOT_PASS; listening/production WAV and end-to-end pipeline integration pending |
| P1 packaging | OPEN; truthful title and thumbnail |
| P1 long-form | OPEN; no original long-form render yet |
| P1 independent editorial and rights | BLOCKED_HUMAN_REVIEW |
| P2 costs/time | OPEN; actual owner PC end-to-end measurement |
| Phase 13 Windows/browser/restore/YouTube | OPEN; no owner device or OAuth acceptance |
| Phase 14 release | BLOCKED; full repo regression, package manifest refresh, integration and owner acceptance required; no public upload |

No change to the historical 13–20 November backup blocker. Keep main Phase 13 intact until review. No publishing permission is emitted by either module.
