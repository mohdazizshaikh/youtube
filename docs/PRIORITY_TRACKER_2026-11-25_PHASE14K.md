# Phase 14K — unified bilingual review, recovery and owner retiming (2026-11-25)

Base 3d958293e324dd76ffa0dea47cc244d1efc70acd; [Phase 14J integrated CI run 45479373876](https://github.com/mohdazizshaikh/youtube/actions/runs/45479373876) succeeded. Draft PR #7; main remains Phase 13. Three independent engineering workstreams executed; no external models downloaded, account access, real inference, production DB migration, legacy queue registration or release authority.

## Executed evidence

- New versioned bilingual workspace stages exact English V6/Hindi mastered video, original receipts and timelines, thumbnails and bilingual metadata using an explicitly pinned config. Checks declared English/Hindi provenance chains, chapter timestamps, 24-shot continuity and padding arithmetic, then runs both full technical decode/format/timing/loudness audits in two parallel workers. English SHA256 ebbbd504895d54472a127492efeb647037a57e132bdef84858d2aef7a19fc50d, 22536166 bytes, 11209 frames, 373.633s, -16.73 LUFS/-1.39 dBTP; Hindi SHA256 6a849cd4b826e7018da969304378d987096832ef3d836f77581997a9a393a7af, 18350399 bytes, 9829 frames, 327.633s, -16.85 LUFS/-1.38 dBTP. Both fresh full decode and numeric audio gates passed. No re-encode or new artistic improvement claimed. Receipt chains are declared evidence, not independent provenance; original Hindi pre-master video and individual narration WAVs are not staged or independently re-audited by this workspace.
- Local-only API and basic bilingual browser UI: language selector, chapter seek controls, frame-specific feedback, shared append-only SQLite ledger, revision CAS, bounded notes, session token, literal loopback Host/Origin checks and CSP. Actual in-process ASGI tests retrieved both complete exact video byte streams, saved two automated language-specific notes, rejected stale writes and found no approval route. Restart from restored workspace returned revision 2. No human feedback, real browser playback, browser seeking or physical Windows acceptance; previous Chromium environment restriction persists as an unclosed gate, not re-tested here. The API reads each entire verified video (128 MiB cap); owner-controlled local filesystem assumed; no encrypted storage or hostile-local-process isolation.
- Recovery: snapshot of fixed 12-file inventory (10 inputs, workspace descriptor and SQLite database) using SQLite backup API; externally pinned backup manifest, exact bytes restored into fresh directory, all hashes and DB identity/quick-check/notes verified, revision history equal. Actual workspace SHA256 323a44ba791a19e90358aa5fb21eb0881e99ed7052d633e2848976ef8e91c8eb; backup manifest SHA256 d3b34062b4d15039ac7dcf6af93805dd4b02689c4337b12326b3ebadc68598be. Actual API+backup/restore/restart exercise 0.8s on isolated host (excludes initial full media audits). Tests reject overwrite and tampered backup. No disaster recovery of actual owner production data. Preserve manifest hash separately; hashes alone do not authenticate maliciously replaced evidence.
- English owner chapter retiming: new offline splitter validates existing owner intake, pinned boundary manifest and exact chapter WAV hashes, explicit reviewed 0-based sample and whitespace-token boundaries for three shots per chapter, writes 24 PCM16 mono 48kHz WAV/text pairs and padded assembled narration with per-shot provenance and hashes. The unit fixture uses eight artificial constant-sample WAVs (not human speech), 144003 samples/chapter, 24 cuts, 744 frames (24.8s), exact total raw sample preservation and zero-padding. No generated captions, speech recognition, semantic cut verification, owner recording acceptance or actual film reassembly. Owner boundary/rights/listening fields are declarations. No local Piper executable found; natural voice model and real CTC inference still unavailable. Never reuse synthetic word timings for actual recordings.
- 16/16 new isolated tests and 53/53 combined Phase 14I/J/K tests passed. All three new source/test Git blobs matched local tested bytes. Existing full repository checkout DNS blocker previously observed, not re-tested here. Latest integrated CI and updated manifest validation pending. Source transfer used personal Library copies of three tested source/test files; no private speech or reviewer records transferred to Git.

## Reproduce

Use trusted Python, FastAPI/uvicorn/httpx, FFmpeg/ffprobe and previous Phase 14J dependencies. Work in a private owner-controlled directory outside Git; use new output directories, preserve INCOMPLETE failures. No automated downloads.

Create a JSON config with exactly these 10 keys, each mapping to an object with path (owner local file) and sha256 (externally verified lowercase 64-digit hash):
- metadata.json: Phase 14J bilingual metadata V2
- en.mp4, en_receipt.json, en_timeline.json: Phase 14H polished_review.mp4 and receipt; Phase 14E motion receipt
- hi.mp4, hi_render.json, hi_master.json, hi_timeline.json: Phase 14J mastered video, raw render receipt, mastering receipt and Phase 14I prepared receipt
- en.png, hi.png: Phase 14I thumbnail concepts

    python -m tools.phase14_workspace prepare --config <config.json> --expected <config-sha256> --output <new-workspace>
    python -m tools.phase14_workspace serve --root <workspace> --pin <workspace-json-sha256> --port 8767
    python -m tools.phase14_workspace backup --root <workspace> --pin <workspace-json-sha256> --output <new-backup>
    python -m tools.phase14_workspace restore --source <backup> --expected <backup-json-sha256> --output <new-restored-workspace>
    python -m tools.phase14_owner_retime --plan tools/phase14_film_plan.json --manifest <english-owner-manifest> --assets <private-chapter-wavs> --boundaries <reviewed-boundaries-json> --expected <boundaries-sha256> --output <new-retimed-assets>
    python -m pytest -q tests/test_phase14_workspace.py tests/test_phase14_bilingual.py tests/test_phase14_localize.py

Boundary JSON: schema VIRALOS_OWNER_SHOT_BOUNDARIES_V1, owner_manifest_sha256, basis owner_reviewed_manual, boundary_review_attested true, chapters array of eight ordered objects. Each object has chapter (1–8), wav_sha256, sample_boundaries [0,cut1,cut2,total_samples] and word_boundaries [0,token_cut1,token_cut2,total_whitespace_tokens]. All four boundaries integer and strictly increasing, each PCM shot 1–90s, total 24s–15min. Native reviewer must verify real cuts against original speech; the module does not infer or authenticate them. No owner media or private rights records in Git. Actual owner playback on http://127.0.0.1:8767/ remains required.

## Consolidated priorities

| Priority | Gate | Current status / next proof |
|---|---|---|
| P0 | Integrated CI/package | Phase 14J green; Phase 14K manifest refresh and latest CI pending |
| P0 | Natural English/Hindi voices | BLOCKED_OWNER_MODEL_OR_RECORDING; no licensed local model or real owner recordings available |
| P0 | Owner retiming | EN_MANUAL_BOUNDARY_FIXTURE_TESTED; actual approved cuts, full reassembly and word alignment pending |
| P0 | Acoustic alignment | Reference/candidate evaluator ready; actual local model inference and independent annotations pending |
| P0 | Caption quality | Both full films synthetic; real timing and native review required |
| P0 | Cinematic visuals | English progress-lane motion, Hindi static boards; differentiated scene-specific animation pending |
| P0 | Technical audio | Fresh bilingual numeric gates passed; natural speech and human listening pending |
| P1 | Bilingual editorial workspace | API and media pins tested; real browser and human revision/acceptance pending |
| P1 | Recovery | Actual isolated synthetic workspace backup/restore verified; physical owner restore and production DB recovery pending |
| P1 | Packaging | Bilingual metadata and thumbnails pinned; independent review and CTR unmeasured |
| P1 | Windows/hardware | BLOCKED_OWNER_HARDWARE; actual installation, playback, restore and CPU/RAM logs |
| P1 | YouTube | BLOCKED_OWNER_AUTHORIZATION; no live private upload/analytics |
| P2 | Resource optimization | Two parallel media audits; owner PC performance unmeasured |
| Recovery | 13–20 Nov source history | BLOCKED_OWNER_BACKUP |
| Release | Merge | OPEN; latest CI, reviewed integration and owner acceptance; main preserved |

Next: obtain actual licensed bilingual speech or owner recordings and independently reviewed reference annotations; implement real narration-to-film assembly, representative real CTC inference, differentiated visuals and native editorial acceptance. Continue physical Windows/browser/restore and separately authorized private account tests only with owner evidence. No synthetic release or 12-domain expansion. See [project status](PROJECT_STATUS.md) and [owner acceptance checklist](OWNER_ACCEPTANCE_2026-11-25_PHASE14J.md).
