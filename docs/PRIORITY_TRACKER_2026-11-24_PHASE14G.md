# Phase 14G — complete synthetic captioned review film (2026-11-24)

Base: Phase 14F 2804f2cf9b1b1ce981fbb86e8b063bc7682e9bb5. [CI run 45457839998](https://github.com/mohdazizshaikh/youtube/actions/runs/45457839998) succeeded. Draft PR #7, main preserved at Phase 13. No account access, database changes, release permission or external model downloads.

## Executed results

- New offline review renderer verifies original Phase 14E raw-video SHA256, pinned plan and synthetic voice declaration, mastering receipt source/output hashes and numeric gate, recompiles captions from Phase 14F fixture and exact assembled PCM, and rejects nonsynthetic intake. The chain checks declared receipts and bytes, not independently authenticated authorship or semantic speech matching.
- Full 932-word/24-shot artificial caption timeline burned into complete motion film. 1920x1080/30fps, 11209 frames, 373.633333s video, 373.653s audio. Source scaled to 1728x972 and centered horizontally on 1920x1080 canvas, dedicated 108px bottom caption strip, warning extended through every video frame. Full decode passed. Render plus fresh audit 46.18s on isolated Linux host. Eight decoded midpoint frames visually inspected: captions separate from boards; focus rings still obscure some source text; complete human playback pending.
- Actual output SHA256 89a6b3c56804e266629e461fb7d1f5907f8f207caa83b91bc4e8574b4701a474; source mastered SHA256 50248ba5eca262535db05259f875f3e45e2bd73a47422bc68758ef8b6518d11e; timeline SHA256 d0657dc3cc834fbe21c748fbe66bab681baba47be157a93de1422e37736e01ca; review ASS SHA256 035a71129dbb689669016a7e01d68476a1e3927fbd542a54b699273133f7fa5f. Encoded AAC payload SHA256 052a7cfecabcd2bb1ddeb7a33b2c78e3a70839117621aadccd6d942d612d8448 matched before/after stream copy. This is payload equality, not independent per-packet timestamp or semantic verification.
- Fresh final audit: -16.73 LUFS, -1.39 dBTP, 1.8 LU LRA; numeric gate and full decode passed; no listening acceptance. 11/11 isolated regression tests passed, source and test Git blobs matched local tested bytes. Full local checkout still DNS-blocked; latest integrated CI pending.
- Existing Phase 13 pilot_pipeline and domain_review_web inspected: console expects a DraftPlan/compose manifest and staged WAVs audited by domain_draft_review. Phase 14G produces a separate receipt, not that schema. Do not forge a legacy manifest, auto-register or approve synthetic media. queue_enqueued=false, publication_authorized=false; existing private console integration remains open.

## Reproduce

Trusted Python, Pillow, FFmpeg/ffprobe, libass, local fonts, existing Phase 14E/14F assets; new output directory in private owner-controlled filesystem. No network or model downloads. Failed render retains INCOMPLETE. Run from repository root:

    python -m tools.phase14_review_render --plan tools/phase14_film_plan.json --raw /private/motion/motion_film.mp4 --mastered /private/mastered/mastered.mp4 --timeline /private/motion/receipt.json --master-receipt /private/mastered/receipt.json --narration /private/motion/work/narration.wav --manifest /private/caption-fixture/manifest.json --assets /private/caption-fixture/assets --output /private/review
    python -m pytest -q tests/test_phase14_review_render.py

Receipt contains fresh final technical audit, caption hash links, audio payload equality and explicit false release/alignment/queue flags. No publication eligibility. Keep synthetic video and private owner evidence outside Git.

## Review handoff checklist

Review the exact output hash locally: watch all chapters, record time-coded errors and revisions; confirm claim/source correspondence and original visuals; check caption legibility, actual spoken-word timing and title/thumbnail truthfulness. This fixture must remain marked NOT ALIGNED; only real licensed bilingual speech with acoustic benchmark and native reviewers can close voice/alignment gates. Never approve this synthetic candidate for release. Adapt existing private console using an explicitly versioned media intake contract and fresh audit; retain current restrictions and verify actual browser playback.

## Priority tracker

| Priority | Work | Status / remaining proof |
|---|---|---|
| P0 | CI/package | Phase 14F green; Phase 14G manifest refresh and latest CI pending |
| P0 | Natural English/Hindi voices | BLOCKED_OWNER_MODEL_OR_RECORDING; actual licensed speech and native listening |
| P0 | Acoustic alignment | BLOCKED_REAL_SPEECH_AND_BENCHMARK; no measured word accuracy |
| P0 | Full captioned film | SYNTHETIC_FULL_LENGTH_RENDER_PASS; real timings, actual Hindi and readable full review pending |
| P0 | Visual quality | CAPTION_STRIP_FULL_FILM_TESTED; source focus marker overlaps, differentiated scenes, native Hindi graphics and semantic cues pending |
| P0 | Story/editorial | Original English draft; claim/pacing and Hindi adaptation review pending |
| P0 | Audio | NUMERIC_PASS_AUDIO_PAYLOAD_PRESERVED; human listening and real voice mix pending |
| P1 | Private review console | CONTRACT_INSPECTED; versioned adapter and isolated queue/browser tests pending |
| P1 | Thumbnail/title | Draft; professional original package review pending |
| P1 | Rights/editorial | BLOCKED_HUMAN_REVIEW |
| P1 | Windows/browser/restore | OPEN; actual owner hardware acceptance |
| P1 | Authorized YouTube | BLOCKED_OWNER_AUTHORIZATION; no live upload or analytics |
| P2 | Resource optimization | 46.18s isolated caption render+audit; actual owner hardware cost unmeasured |
| Recovery | 13–20 Nov source history | BLOCKED_OWNER_BACKUP |
| Release | Merge | OPEN; review, latest CI and acceptance required; main preserved |

Next: explicit Phase 14 review adapter, collision-safe visuals, licensed bilingual narration and real alignment, native and editorial acceptance. No synthetic approval, public publishing, real revenue or general autonomous director claimed. See [project status](PROJECT_STATUS.md).
