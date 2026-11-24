# Phase 14F — global word-caption timeline and narration intake

Base: Phase 14E a023a7307e553c028a55a90e434dfff9a7eb323b, [CI run 45452478092](https://github.com/mohdazizshaikh/youtube/actions/runs/45452478092) succeeded. Continue draft PR #7; main remains Phase 13. No database changes, real account access, model downloads or publishing authorization.

## Executed results

- Compiled full 24-shot, 932-word English timeline using Phase 14E's actual assembled PCM WAV and declared shot sample counts. 11209 frames, 373.633333s, last caption 373.61s. Assembled narration PCM exactly matches all individual shot PCM bytes and zero padding. The synthetic fixture reconstructs segments from the assembled WAV and creates evenly distributed artificial word timings; this is not independent source-audio or acoustic alignment proof.
- Caption compiler validates pinned English plan and exact English token coverage, safe filenames, asset SHA256, timing manifest, source locale, exact PCM format and sample count, gap/overlap and global centisecond boundaries. Hindi Unicode input and font contract tested; Hindi translation correctness, speech, and shaping across platforms not certified. Owner-reviewed manual/CTC declarations require private rights and listening fields but are not independently authenticated. No acoustic model inference.
- Caption groups contain up to four tokens and 42 Unicode code points, split at shot boundaries and gaps >400ms. ASS active word highlighting; synthetic fixture has explicit non-alignment warning. No final reading-speed or line-width guarantee.
- Actual 12-second excerpt from mastered Phase 14E video rendered at 1920x1080/30fps, 360 frames, H.264/AAC and complete FFmpeg decode passed. A second layout scales source to 1728x972 and pads to 1920x1080, leaving 108px bottom strip for captions. Sampled frame at 5 seconds confirms separation from existing watermark; all-scene overlap, source marker overlap and human watch-through remain open. This is a sample, not full-film burn-in or a semantic audio/caption match. No new master quality measurement on the excerpt.
- Local pytest 21/21 passed. Full checkout still fails DNS resolution; latest integrated CI, package validation and review remain necessary. Prior Phase 14E CI success verified.
- Receipt: narration SHA256 e3b7e8bc1042978b89ff5a18da5fc5da1663f3ca2bb357ecbc40f704f2ed90ef; timeline SHA256 d0657dc3cc834fbe21c748fbe66bab681baba47be157a93de1422e37736e01ca; ASS SHA256 74166357edf31666db2ca91daf9f80b002d93641eec183d236af1be6ef0f91c9; word JSON SHA256 6039c30443f2a70107be62cc35a7bb08543dba11bf3a56eff409f2ed20d40954. Files are private local artifacts, not committed media.

## Reproduce

Use trusted Python, FFmpeg with libass and local Noto Sans/Noto Sans Devanagari fonts. Work in a private directory; output directories must not exist. Retain incomplete outputs for investigation. No owner assets or credentials in Git.

    python -m tools.phase14_caption_fixture --plan tools/phase14_film_plan.json --timeline /private/motion/receipt.json --narration /private/motion/work/narration.wav --output /private/caption-fixture
    python -m tools.phase14_caption_timeline --plan tools/phase14_film_plan.json --timeline /private/motion/receipt.json --narration /private/motion/work/narration.wav --manifest /private/caption-fixture/manifest.json --assets /private/caption-fixture/assets --output /private/captions
    python -m pytest -q tests/test_phase14_caption_timeline.py

For synthetic visual sample only, run from private working directory containing the compiler-generated captions/ folder:

    ffmpeg -i /private/mastered/mastered.mp4 -t 12 -vf "scale=1728:972:flags=lanczos,pad=1920:1080:96:0:color=0x0b1829,ass=captions/global_highlight.ass" -c:v libx264 -preset ultrafast -crf 23 -c:a aac -b:a 160k caption_safe_preview.mp4
    ffmpeg -v error -xerror -i caption_safe_preview.mp4 -f null -

Owner intake contract: schema 1, locale en-US/en-IN/hi-IN, basis owner_reviewed_manual or owner_reviewed_ctc, plan/timeline/narration SHA256, explicit rights_attested and listening_attested plus private rights_reference, exactly 24 ordered shots with txt/wav/json hashes. Each shot contains NN.txt, NN.wav, NN.json in private assets; PCM16 mono 48kHz and exact sample counts; timestamp JSON as Phase 14B contract. Current film timeline is pinned to original English reference; separate localized narration may require new shot durations and new render. Never claim translated Hindi or acoustic word alignment from token/timing declarations. Do not apply English fixture to actual localized film.

## Current priority tracker

| Priority | Work | Status / remaining proof |
|---|---|---|
| P0 | Natural English/Hindi narration | BLOCKED_OWNER_MODEL_OR_RECORDING; licensed real voice, native audition, actual CTC benchmark |
| P0 | Full-film word caption integration | GLOBAL_TIMELINE_TESTED; 932 artificial words and 24 shots, actual aligned owner narration and complete burn-in/QC pending |
| P0 | Visual refinement | DEDICATED_CAPTION_STRIP_SAMPLE_TESTED; 12s sample; full-film visual review and text-safe focus markers pending |
| P0 | Story | Original English draft; independent claim/pacing review, native Hindi adaptation pending |
| P0 | Audio | Phase 14E full-film numeric pass; listening review and real voice final mix pending |
| P0 | CI/package | Phase 14E green; Phase 14F refreshed manifest and latest CI verification pending |
| P1 | Thumbnail/title | Draft; professional packaging review pending |
| P1 | Private editorial console | OPEN; integrate fresh technical audit without weakening synthetic restrictions |
| P1 | Independent editorial/rights | BLOCKED_HUMAN_REVIEW |
| P1 | Windows/browser/restore | OPEN; actual owner hardware acceptance |
| P1 | Authorized YouTube | BLOCKED_OWNER_AUTHORIZATION; no live upload or analytics |
| P2 | Cost/time optimization | Existing isolated benchmark; actual owner PC and production costs unknown |
| Recovery | Missing 13–20 Nov history | BLOCKED_OWNER_BACKUP |
| Release | Merge and packaging | OPEN; review, verified latest CI, integrated release acceptance; main preserved |

Next: integrate a synthetic-only complete captioned film assembly and review handoff, obtain licensed real bilingual speech, actual alignment/word timing and independent editorial acceptance. No public publishing, professional voice certification, general autonomous creative director, revenue or GPU claims. See [project status](PROJECT_STATUS.md).
