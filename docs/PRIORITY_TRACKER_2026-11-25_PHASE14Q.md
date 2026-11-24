# Phase 14Q — fresh bilingual QC, audio packet integrity and resumable media review (2026-11-25)

Base cec4e86c6a70b1046008b3f195a3f2e0d89a1671; [Phase 14P CI run 45489348083](https://github.com/mohdazizshaikh/youtube/actions/runs/45489348083) succeeded. Draft PR #7; main remains Phase 13. Existing synthetic films unchanged. No external model downloads, actual speech inference, account access, production DB changes or publication authority.

## Executed evidence

- Added pinned bilingual media review orchestration with stage/all CLI, exact 24-shot PCM-derived frame arithmetic, semantic receipt/source/video/thumbnail identities, locally recomputed packet evidence, parallel fresh signal scans and scene policy assessment, and semantic handoff draft rebinding. Initial stage created eight files (two films, receipts, thumbnails, packet reports); resume reused all eight exact bytes and generated six fresh QC/scene/handoff reports. Configuration SHA256 f128a9a287d207f3f185bb166662dce8dcc42bff3418c2bde21569827e1b06ac. Exclusive lock and atomic no-overwrite file creation using same-directory hardlinks; requires supporting owner filesystem, not verified on Windows. All-stage reruns re-scan rather than trust cached QC, and compare cached bytes. Media staging is resumable, not mid-encode or voice-to-publish orchestration. No actual browser UI integration. Source receipt chains are declared and externally pinned, not independently authenticated.
- Fresh Phase 14P English semantic video SHA256 61f2464fecb88f69794d8a69faef7cc6c9f0b1318bf58fa642b3d42fb4a98bf2: 11209 frames, 373.633333s, audio 373.653s, full decode and numeric audio pass (-16.73 LUFS/-1.39 dBTP, LRA 1.8 LU). No near-full-scale samples, detected black intervals or quiet intervals >=2s; sample peak -1.396 dBFS, longest quiet 0.4s. 111 freeze start/end events, 9613 frames covered by detector intervals (85.7614%), 21/24 motion-expected shots flagged. QC SHA256 8bd72b37faf65f3359177040d846102e3df57b37eaa19b4b2dadbc2486a0367e; scene b44822e5a68914d43a64d67594fea4260e98e0fad0b6adc912bd1e3a6fa3623e.
- Hindi semantic video SHA256 168b1544d94913b542a10b2917f50095cc1da29ea1a26293f7885bb089c00d09: 9829 frames, 327.633333s, audio 327.637s, full decode and numeric audio pass (-16.85 LUFS/-1.38 dBTP, LRA 1.6 LU). No near-full-scale samples, detected black intervals or quiet intervals >=2s; sample peak -1.386 dBFS, longest quiet 0.5s. 119 freeze start/end events, 8875 frames covered (90.294%), 21/24 motion-expected shots flagged. QC SHA256 d4484d4732a0a52e1056a8e79ecd3292713613d7abe3d5bc829066281d32ecb3; scene aace731965c49b234e3dd46d1b161bb675206b85191ef887d57feda6ffa87f43. Detector tolerances and EOF closure mean coverage is not a count of identical decoded frames. All 48 shots intentionally assigned semantic_motion_expected; no suppression of original flags or creative acceptance. No new animation rendered; continuous native-resolution motion and complete native/factual review remain open. Hindi remains shorter than original 6–8min target.
- AAC packet evidence: ffprobe stream time base 1/48000, codec/sample rate/channels, packet-level compressed SHA256, integer PTS/DTS/duration, size and exposed side-data fields included in deterministic comparison. Both source and semantic output signatures exact match; also independent concatenated encoded payload hash check. English 17516 packets, signature ff861f07eb62680758ede9c2e4c558430d961369d2415261f756eeaee6a90dc9; Hindi 15359 packets, signature 2706b58af6e4edef43a58a6606a37e1d2a7c59b3fff65fc1e41ec66edc2351ed. Packet report hashes en 3e13e193c1acd3d1bf7e1f494ba381580d965179873ef54ab48cdd2e82a6abcf and hi 529a98a14ed7d83c4744ce0dba8dfb9547d727d462f3f214052fa338478f2bc4. Evidence is scoped to exposed ffprobe fields, not all container metadata or semantic sync.
- Rebound handoff drafts retain original titles/description/thumbnail hashes from pinned Phase 14J metadata, replace video identities, bind eight exact chapter-start frames and floored seconds, fresh scene flags and packet evidence. EN handoff SHA256 aecc91e935e9d7bb9e8248c98939250886cc8d3a8b58e12580a2038c519e0593; HI 2f0c15437e458c93d24d8e98eafbdb825d339a2ee211f8c0d90cd6d6639a71a1. No new thumbnail, final metadata approval, human feedback, caption or real media console adapter. Production accepted=false; publication authorized=false.
- Non-destructive media staging recovery: deliberately corrupted English video copy and missing Hindi thumbnail, six other expected artifacts exact. New directory re-staged both films and all expected evidence from pinned source inputs and recomputed packet comparisons. Six exact, one mismatch, one missing; old source inventory and lock byte hashes verified unchanged. Recovery receipt SHA256 3727dcef41952b092752bd1e7ca9a3fdd31ed7e7da83953f2c7d3b74a452a299. This is a staged-media test, not real owner backup recovery or interrupted FFmpeg encode recovery; source inputs must still exist. Do not automatically clear old lock. 
- 13/13 new tests, 156/156 combined Phase 14I–Q local tests passed in 2.81s; both Git blobs match local tested bytes. Two personal Library source/test copies used for Git transfer. Full local checkout previously DNS-blocked, not re-tested. Piper not found on PATH, actual licensed models/recordings and independent acoustic references unavailable. No actual Windows/browser/authorized private account evidence. Latest Phase 14Q integrated CI pending after manifest refresh.

## Reproduce

Trusted Python, FFmpeg/ffprobe, prior Phase 14P and Phase 14J assets, local owner-controlled filesystem supporting hardlinks, fresh private output locations outside Git. Keep independently retained source pins. No automatic downloads, no private media/rights records in repository.

Config exact keys schema VIRALOS_MEDIA_REVIEW_RUN_V1, locales (en/hi), metadata (Phase 14J bilingual metadata V2). Each locale exactly video (Phase 14P final semantic_review.mp4), source (English Phase 14H polished_review.mp4 or Hindi Phase 14J mastered.mp4), receipt (Phase 14P final receipt.json), thumbnail (Phase 14I PNG). Each entry including metadata is a path/sha256 envelope. 
    python -m tools.phase14_media_run --config <private-config.json> --expected <config-sha256> --output <new-private-review> --stage stage
    python -m tools.phase14_media_run --config <private-config.json> --expected <config-sha256> --output <same-private-review> --stage all
    python -m tools.phase14_media_run --config <private-config.json> --expected <config-sha256> --output <fresh-recovery-folder> --recover-from <interrupted-stage-folder>
    python -m pytest -q tests/test_phase14_media_run.py

Recovery only restages the expected eight artifacts and recomputes packet evidence; then use --stage all on recovered folder for fresh QC and handoff. Keep old lock and evidence untouched. Do not assume a lock indicates the original process is stopped. Atomic creation and validation assume trusted private directories, not malicious local filesystem isolation. Report flags require human review and cannot authorize publication.

## Consolidated priorities

| Priority | Gate | Status / next proof |
|---|---|---|
| P0 | CI/package | Phase 14P green; Phase 14Q latest CI pending |
| P0 | Natural bilingual voice | BLOCKED_OWNER_MODEL_OR_RECORDING; actual licensed model, inference and native listening |
| P0 | Real alignment | Actual CTC inference and independent representative bilingual annotations |
| P0 | Owner films/captions | Both paths fixture-tested; actual speech, true timing and full renders pending |
| P0 | Continuous native-resolution motion | NOT IMPLEMENTED in 14Q; 21/24 motion-expected shots flagged per language; prioritize smooth meaningful motion, not detector gaming |
| P0 | Signal QC | Fresh both full-length films, decode/audio pass; extensive freeze review flags; human perceptual and reading-speed review pending |
| P0 | Audio preservation | Both exact packet signatures and payloads matched; real speech mastering/listening pending |
| P1 | Orchestration | Resumable staging/QC/handoff and actual restaging drill tested; render/inference-stage and mid-encode recovery pending |
| P1 | Editorial/packaging | New semantic draft handoff pins; real workspace adapter and native/factual/rights review pending |
| P1 | Windows/browser/recovery | Physical owner installation/playback/restore and measured performance pending |
| P1 | YouTube | BLOCKED_OWNER_AUTHORIZATION; no live upload or analytics |
| P2 | Optimization | Owner CPU/RAM/disk/cost unmeasured |
| Recovery | 13–20 Nov source | BLOCKED_OWNER_BACKUP |
| Release | Merge | OPEN; latest CI, owner/editorial acceptance required; main preserved |

Next: actual licensed bilingual voice and independent alignment evidence; native-resolution continuous scene-specific motion with human review; media render checkpointing, real-media editorial adapter, physical Windows/browser/restore and authorized private account acceptance. See [project status](PROJECT_STATUS.md), [owner checklist](OWNER_ACCEPTANCE_2026-11-25_PHASE14J.md). No synthetic release, public publishing or expansion across 12 domains.
