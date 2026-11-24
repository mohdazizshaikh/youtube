# Phase 14S — 192-operation bilingual shot review batch and recovery (2026-11-25)

Base 482532386689c45de60bbf014133527d9da161f7. Draft PR #7; main remains Phase 13. Three new modules and two test files. No account access, external model downloads, natural speech inference, real alignment, production changes or publication authority.

## Executed batch

- Actual English/Hindi full-film sources from Phase 14P, pinned receipts and Phase 14R 48-task OPEN backlog. Two locale workers in parallel. Each shot separately extracted to lossless H.264/YUV420p silent MP4, 1920x1080 at 30fps. Source decoded frame sequences independently hashed SHA256 in output 1/30 timebase; every extracted shot probed and fully decoded, compared frame-by-frame to exact contiguous source range. Midpoint PNG generated and format/dimensions validated; source, task, clip, midpoint and frame-sequence digests bound to per-shot receipt. Full source file hashes rechecked after processing. Hash comparison covers decoded pixel bytes, not source compressed video packet identity or independently verified original container timestamps. No creative changes, audio or new caption track in clips.
- 24 English shots / 11209 frames and 24 Hindi shots / 9829 frames. 48/48 new shot receipts, 21038 decoded frame matches. Four scoped operations per shot: extract, decoded frame sequence verification, midpoint generation/validation, editorial task binding = 192 verified operations. This is not 192 independent software features or closed human/editorial tasks. All 48 remain OPEN (42 P0 motion flags, six P1 editorial). Runtime 432.01s on isolated Linux, includes source frame hashing and shot validation; no physical owner hardware benchmark. Config SHA256 e0fff7546feb4a5eaa59765cfa65dc34371bc21ab22bb7dd5b0199d181c3df12; batch SHA256 621568868c3bea42e0064c96604c930384395dd46e374ea237ad186a9252b596. Operation ledger SHA256 ce0418a1f881e1caaf545e0b8ead7b0baf26d6af88ef5e64454f88d444231990. The full batch created all 48 rather than testing a second full resume. Small actual FFmpeg fixture exercises revalidation and partial/cached mismatch rejection.
- Static offline index generated from pinned batch and backlog, verifying all 48 receipt/clip/PNG hashes and task identities. 48 cards, 48 images, 144 local link instances verified by HTML parsing and existence checks. No JS, approval, publishing, or remote requests. Index SHA256 ec91f347b8539b0214d0f242cbf4937e19872ef4b2f33bc820b23c0ddd1e886f. Two 24-shot contact sheets and a local ZIP with 152 entries, CRC check passed; ZIP 199267432 bytes, SHA256 deb2d5b023e2e4eef79a54bfcaa7653cec0646fae2c80ece854787b7f1f54a0c. ZIP includes index, clips, PNGs, receipts, batch/ledger/backlog, contact sheets and readme. Private review assets delivered outside Git; not committed media. Lossless H.264 High 4:4:4 Predictive profile despite YUV420p may not play on typical browser/hardware decoders; real browser playback not tested. Use supported local player. Source films retain synthetic audio; shot clips are silent. No full-film reassembly or motion improvement claimed.
- Non-destructive partial-shot recovery executed against deliberately damaged Hindi hi-01 copy and independently pinned previously verified receipt afdc1629ac3cdd84ad3c4eac1638b0a251f06793bc8ab82ea3d9049ede9248f6. Reconstructed 470 frames from pinned full-film source; exact decoded sequence SHA256 f676ce9ea32ab7b646b22599f989d2a646d8b396ff686c29481f08457e8850a9; clip and midpoint bytes both matched original reference; interrupted inventory and INCOMPLETE marker unchanged. Recovery receipt e5ced9caa76812a78137e36a4ac4414d72d78259ab913e2decdc15cb3e695104. Rebuilds in new folder, not mid-frame resume or actual owner failure. Requires prior externally pinned reference receipt; if no verified receipt exists, select shot in a fresh batch folder using original pinned source and full frame hashing. Do not overwrite failed artifacts. Lock not automatically cleared after process crash.
- 10 new tests / 185 combined Phase 14I–S local tests passed in 13.26s. Five new source/test Git blobs matched local bytes; five personal Library staging copies created for transfer. Phase 14R integrated CI passed (see prior run history); intermediate Phase 14S head b49df302a58c16a942d69b041c41e095beaae901 CI run 45495097669 succeeded. Latest final manifest commit CI must be verified separately. Prior full local checkout DNS restriction not retested. Actual Windows filesystem, browser and owner hardware unverified. No licensed model/recording or independent acoustic annotations supplied.

## Reproduction

Use trusted local Python, FFmpeg/ffprobe with libx264, Pillow and owner-controlled private storage. Keep source films, original receipts and editorial tasks pinned from independent trusted records. No automatic model downloads. Config schema VIRALOS_SHOT_BATCH_V1, locales en/hi each with video and receipt pin envelope (path, sha256), tasks pin envelope for Phase 14R backlog.

    python -m tools.phase14_shot_batch --config <private-config.json> --expected <config-sha256> --output <private-review-root> > <batch-result.json>
    python -m tools.phase14_shot_index --root <private-review-root> --report <batch-result.json> --expected <result-sha256> --tasks <editorial-tasks.json> --tasks-sha <tasks-sha256> --output <private-review-root>/index.html
    python -m tools.phase14_shot_recovery --config <private-config.json> --expected <config-sha256> --select hi-01 --receipt <trusted-reference-shot-receipt> --receipt-sha <pin> --interrupted <failed-shot-folder> --output <fresh-recovery-folder>
    python -m pytest -q tests/test_phase14_shot_batch.py tests/test_phase14_shot_recovery.py

Completed batch reruns independently revalidate actual decoded sequence and exact receipts; no cached success shortcut. Optional --select en-01 or hi-01 etc uses one locale and full source hashing. Use new directory for incomplete shot and preserve old lock/failure evidence. Static index reads exact source references; it does not store reviewer feedback or replace the prior editorial web workspace. No production acceptance.

## Priorities

| Priority | Gate | Status / next proof |
|---|---|---|
| P0 | CI/package | Phase 14R green; Phase 14S intermediate CI green; final manifest CI pending |
| P0 | Natural bilingual voice | BLOCKED_OWNER_MODEL_OR_RECORDING |
| P0 | Real alignment | Actual local inference and independent reference |
| P0 | Owner films and captions | Real narration, genuine timing and reassembly pending |
| P0 | Motion | All 42 original flags remain open; meaningful scene-specific creative revisions needed |
| P1 | Shot review | 48 clips and task bindings verified; static index generated, human review and feedback pending |
| P1 | Recovery | Single actual synthetic shot drill passed; physical owner restore and full-film checkpointed reassembly pending |
| P1 | Browser/Windows | Real browser, compatible playback, physical installation and resource measurement pending |
| P1 | YouTube | BLOCKED_OWNER_AUTHORIZATION |
| Recovery | 13–20 Nov source | BLOCKED_OWNER_BACKUP |
| Release | Merge | OPEN; final CI, owner/editorial acceptance required; main preserved |

Next: get actual licensed bilingual voice and acoustic references, address 42 motion flags through human-reviewed scene redesign, integrate checkpointed film reassembly and browser-compatible proxies, then owner Windows acceptance and authorized private account testing. No synthetic release/public publishing or 12-domain expansion. See [project status](PROJECT_STATUS.md) and [owner acceptance checklist](OWNER_ACCEPTANCE_2026-11-25_PHASE14J.md).
