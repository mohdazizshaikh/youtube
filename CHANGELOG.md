# Phase 14O — semantic motion, scene-aware QC and resumable review (2026-11-25)

- Verified Phase 14N CI run 45484729596 succeeded.
- Added original English three-shot semantic preview with character/hex-byte comparison and real digest XOR reveal (125/256 bits), 42.733s/1282 frames, source 960x540 upscaled to 1080p/30fps. Raw decode passed but true peak failed; corrected master freshly decoded and passed -16.30 LUFS/-1.44 dBTP. Synthetic source narration, no aligned captions; static review flags remain.
- Added explicit scene-motion policy and freeze interval triage, including EOF handling and exact shot accounting. Existing 48 static-board shots reviewed under declared policy; original flags retained, not artistic approval.
- Added fixed two-locale report orchestration, pinned config and inputs, deterministic exact-byte stage reuse and lock/tamper checks. Actual scene-only then resume-all run verified; not full render orchestration or automatic crash recovery.
- 18 new/126 combined local tests passed; all three Git blobs matched local bytes. Updated project status, tracker and integrity manifest; latest CI pending. Main preserved and release blocked.

# Phase 14N — integrated captions, signal QC and acceptance status (2026-11-25)

- Verified Phase 14M CI run 45483722897 succeeded.
- Added pinned bilingual caption burn-in with local ASS regeneration and audio payload equality. Hindi 72.8s/2184-frame artificial fixture with 772 cues fully decoded; numeric audio gate failed. Separate caption/warning/progress regions sampled. English contract tested only; no actual acoustic alignment.
- Added decoded PCM sample peak/near-full-scale and sustained quiet checks, downscaled black/freeze detection and fresh media audit. Actual long-form English/Hindi scans in parallel both passed numeric audio and decode; zero detected black/long quiet/full-scale flags, static/freeze review events remain.
- Added pinned readiness summaries using prior Linux preflight; production acceptance and publication always false. No physical owner deployment or real human acceptance.
- 20 new/108 combined local tests passed; both local/Git source blobs matched. Updated project status, tracker and manifest; latest CI pending. Main preserved.

# Phase 14M — Hindi owner assembly, declared timing and dependency preflight (2026-11-25)

- Verified Phase 14L integrated CI run 45482666390 succeeded.
- Added pinned Hindi owner narration assembly and two parallel encoders, exact per-shot PCM validation and frame rounding; 72.8s/2184-frame Full HD artificial-tone fixture decoded. Audio numeric gate failed; no speech or real alignment claim.
- Added bilingual declared reviewed word timing compiler with exact source/script/WAV pins, sample-boundary validation, global frame offsets and width-bounded cue groups. 772 artificial Hindi cues compiled; six-second overlay decoded and sampled. Full-film integrated real caption burn-in and independent alignment remain pending.
- Added read-only environment preflight for FFmpeg, encoders, ASS, RAQM, local font loading and package versions. Linux dependencies detected; Piper unavailable; owner hardware not tested.
- 19 new/88 combined local tests passed; four local/Git blobs matched. Updated project status, tracker and integrity manifest; latest CI pending. Main preserved and release blocked.

# Phase 14L — English owner narration assembly and local voice runtime (2026-11-25)

- Verified Phase 14K CI run 45481721345 succeeded.
- Added pinned retime/shot/script/WAV validation and byte-exact assembled PCM verification; two parallel encoders rendered 24.8s/744-frame artificial-tone fixture with 24 shots and full decode. Numeric audio gate failed; no mastering or word captions claimed. Real narration and continuous semantic motion remain pending.
- Added explicit opt-in local Piper adapter with executable/model/config/script hashes, rights declarations, timeout and PCM normalization path. Contract tests passed; no real model execution or voice certification, no automatic downloads.
- 16 new/69 combined local tests passed; all three new Git blobs matched local bytes. Updated project status, tracker and integrity manifest; latest CI pending. Main preserved; release blocked.

# Phase 14K — bilingual review workspace, recovery and explicit owner retiming (2026-11-25)

- Verified Phase 14J CI run 45479373876 succeeded.
- Added versioned bilingual private workspace, exact pinned media/metadata/thumbnail inventory, two parallel fresh technical audits, local-only review UI/API and shared frame-specific revision ledger. Actual media-byte retrieval and two automated language-specific notes tested; stale revision rejected, no approval route. Real browser playback remains pending.
- Added fixed-inventory pinned snapshot, SQLite backup and fresh-directory restore; restored actual 12-file synthetic workspace, revision 2 and note equality. Tamper and overwrite rejection tests passed. No physical owner recovery claim.
- Added explicit English owner chapter-to-shot PCM splitter and exact token/sample boundary contract; 24-shot fixture tested, no real speech, actual alignment, captions or reassembly. Local Piper not available.
- 16 new and 53 combined local tests passed; three Git blobs matched. Updated project status, tracker, README and integrity manifest; latest integrated CI pending. Main preserved; synthetic release blocked.

# Phase 14J — bilingual film review, owner intake and acceptance handoff (2026-11-25)

- Verified Phase 14I integrated CI run 45464050233 succeeded.
- Restored 24 pinned Hindi boards; two parallel encoders produced 327.633s/9829-frame Full HD/30fps video with 772 artificial word cues and persistent warning. Full decode passed; 116.49s isolated render+audit. Eight chapter samples inspected. Static boards, not natural narration or acoustic alignment.
- Hindi mastering first candidate passed (-16.85 LUFS/-1.38 dBTP); fresh final audit passed. Bilingual metadata V2 binds Hindi mastered SHA and eight timestamps, inherits English metadata. No publication authority.
- Added English owner eight-chapter request/intake, intentionally incomplete manifest and owner acceptance checklist. Real recordings, shot segmentation, actual inference, native editorial review and physical Windows/browser acceptance remain open. 19 new and 37 combined local tests passed; source/test Git blobs matched.
- Updated project status, tracker and integrity manifest; latest CI pending. Main preserved.

# Phase 14I — Hindi localization, owner WAV intake and bilingual packaging (2026-11-25)

- Verified Phase 14H integrated CI run 45462466461 passed.
- Added original 772-word Hindi draft, 24 hash-bound narration segments, actual local synthetic Hindi PCM timeline (327.633s) and 24 shaped 1080p boards. Chapter-one 43.6s/1308-frame preview decoded. Full Hindi video, mastering, native review and genuine alignment pending.
- Added owner WAV intake and 24-script request kit with deliberately invalid placeholder manifest; no actual licensed speech or model certification. Added two original 1280x720 thumbnail concepts based on computed 125-bit example and draft English V6/Hindi metadata. Hindi video/chapter binding intentionally unset.
- 18 isolated tests passed; four local/Git source blobs matched. Updated project status, priority tracker, README and integrity manifest; latest CI pending. Main preserved and no upload authority.

# Phase 14H — parallel editorial studio, visual polish and alignment benchmark (2026-11-25)

- Verified Phase 14G integrated CI run 45459133731 passed.
- Regenerated all 24 shots into V6 full-film review with disjoint graphics, progress and caption regions; two parallel encoders, 11209 frames, 373.633s, fresh full decode and -16.73 LUFS/-1.39 dBTP numeric gate passed, original AAC payload preserved. Eight sampled frames inspected. Not semantic motion or professional visual acceptance.
- Implemented separate versioned private editorial workspace, immutable staged media identity, time-coded SQLite notes, revision CAS and local review UI. Actual V5 and V6 ASGI API media hash and note persistence tests passed; real Chromium navigation blocked by environment. Legacy queue unchanged, no publishing.
- Implemented declared manual-reference versus CTC candidate benchmark. Synthetic 28-word fixture 30ms median/p95; not real acoustic alignment. 17 new isolated tests passed, four code/test blobs matched local bytes. Updated project status, priority tracker and integrity manifest; latest CI pending. Main preserved.

# Phase 14G — full captioned synthetic review render (2026-11-24)

- Verified Phase 14F CI run 45457839998 succeeded.
- Added complete captioned review renderer with input receipt/hash checks, recomputed 932-word synthetic timeline, 108px separate caption strip and persistent timing warning. 373.633s, native 1080p/30fps, 11209 frames, full decode and fresh numeric audio gate passed; encoded AAC payload hash preserved. 46.18s isolated Linux render+audit, 11 isolated tests passed.
- Inspected eight decoded chapter midpoints and Phase 13 review console contract. Focus marker collisions remain; no true alignment, licensed speech, legacy queue registration or publication authority. Updated project status, tracker and package manifest; latest integrated CI pending. Main preserved.

# Phase 14F — global word timeline and caption-safe sample (2026-11-24)

- Verified Phase 14E CI run 45452478092 succeeded.
- Added hash-bound 24-shot narration/word manifest intake and 932-word global synthetic ASS timeline; exact PCM assembly and padding verified. No acoustic alignment or genuine Hindi speech claim.
- Added reproducible timing fixture and 21 passing isolated tests; 12s Full HD sample with separate 108px caption strip decoded; sampled frame inspected. Full-film burn-in and all-scene review pending.
- Updated project status, priority tracker, README and integrity manifest. Main preserved; latest CI pending. No publication authority.

# Phase 14E — complete motion-film assembly and integrated technical audit (2026-11-24)

- Prior Phase 14D CI run 45450166899 passed including package integrity and Windows contracts.
- Added pinned English script segmentation, 24 PCM-driven shots across eight chapters, native 1080p/30fps 373.633s film, 11209 frames, complete decode, segment transcript and chapter timing. 123.58s isolated render+audit; original boards with moving indicators/fades, not a professional cinematic film.
- Reused mastering, final -16.73 LUFS/-1.39 dBTP; fresh final-media hash, stream, duration, frame-count, decode and audio audit passed. 22 new and 60 combined local tests passed. Source/test blobs match. No speech alignment, natural voice, rights/editorial or release authorization.
- Updated consolidated project status, priority tracker, README and integrity manifest; latest integrated CI pending. Main preserved.

# Phase 14D — narration-driven motion and precision editing (2026-11-24)

- Added hash-bound three-shot narration input contract, exact script token coverage, PCM frame rounding and fail-closed checks; English/Hindi input declarations supported, actual licensed voice and word alignment not demonstrated.
- Rendered chapter-one 42.8s, 1920x1080/30fps, 1284 frames with original moving focus graphics and fades; both stream durations matched and full decode passed. Six sampled frames inspected. 14.07s isolated host benchmark; no owner Windows measurement.
- Reused mastering: -16.72 LUFS/-1.45 dBTP final numeric gate passed. 14/14 new, 38/38 combined local tests passed. Added reproducible fixture and tracker. No release authority; complete cinematic long-form and integrated regression/manifest refresh pending.

# Phase 14C — long-form technical rough cut (2026-11-24)

- Added original eight-chapter source-linked 932-word English draft, 24 progressive board beats, native 1080p/30fps 375.8s H.264/AAC render, chapter timestamps and scene transcript, plus draft thumbnail. Full decode passed; 62.23s isolated host benchmark.
- Reused Phase 14B mastering on the complete film: -20.93 to -16.74 LUFS, final -1.40 dBTP; numeric gate and full decode passed, listening review pending.
- Added 12 portable tests (all local pass) and synced the three code/plan/test files. Updated project status, priority tracker and README; PR #7 remains draft, main Phase 13. Full local checkout DNS-blocked; latest integrated CI and release manifest refresh pending.
- No natural bilingual voice, word-level alignment, continuous cinematic motion, independent editorial signoff, Windows owner acceptance or real YouTube integration claimed. No upload authorization.

# Phase 14B — mastering and captions (2026-11-24)

- Added hash-bound numerical mastering and reviewed-word ASS generation; 12 isolated tests passed, synthetic bilingual 1080p caption fixture decoded; CI run 45445134977 passed. No acoustic alignment or voice quality claim.

# Phase 14A — creative preview (2026-11-24)

- Four-scene animated synthetic SHA-256 technical preview, bilingual draft scripts, measured audio quality and four portable checks. CI run 45438729656 passed. No production acceptance.

# Phase 13 — production readiness candidate (2026-11-24)

- Added private pilot composer-to-review workflow with staged hash-checked inputs, fresh technical audit, persistent queue, catalog and incomplete-run marker.
- Added assisted Windows setup, start/resume and isolated acceptance wrappers; trusted prerequisites/manual installation approval, no account access.
- Added a single source-linked technology pilot with original hash experiment and provisional eSpeak narration; no release authority.
- Phase 12 remains stable fallback; owner Windows, licensed voices and live YouTube acceptance pending.

# Phase 12 — private local review console (2026-11-24)

- Added standalone opt-in localhost FastAPI console and browser UI for fixed owner-configured drafts, registration, pinned video review, scene checklist and revision history.
- Added session header, local-origin guard, private catalog scope, bounded request/media handling and no-store/CSP headers; no publication authority.
- Added API tests including real media audit/tamper rejection, and Node syntax validation. Live Chromium navigation blocked by environment policy; no browser or owner hardware acceptance claimed.

# Phase 11 — durable local review operations (2026-11-24)

- Added separate SQLite review ledger and CLI; optimistic revisions, atomic submission history and duplicate detection.
- Fresh media re-audit before registering or submitting a review; synthetic demos cannot be accepted, no publishing authority.
- Keep private database outside repository; no raw reviewer text or media paths stored.
- Added portable queue contract tests and real FFmpeg re-audit regression.

## 2026-11-24 Phase 10 — domain editorial handoff

- Added offline fresh-audit, hash-bound scene review packets and explicit human self-attestation checklists; reject stale, missing and duplicate scene records.
- Added 24-domain-format batch review packet preparation; synthetic demos remain blocked from checklist completion, and no output grants publishing permission.
- Added CLI, portable and media tests, operator instructions and preserved prior package manifest. No owner or suspended account access.

## 2026-11-24 Phase 9 — independent draft audit and AAC timing fix

- Corrected fixed-rate scene timestamps and duration-based termination so short narration is not truncated by a video-frame stop. Tightened stream timing QC.
- Added trusted-pin, inventory, PCM reconstruction, caption and scene timing audit; decoded per-scene audio and sampled visual checks; explicit no-publication result.
- Added offline CLI, automated demo audit receipts and 11 regression/adversarial cases; all 228 tests passed locally.
- No owner-account, old suspended remote, licensed voice model or owner PC access.

## 2026-11-24 Phase 8 — narrated domain draft composition

- Added source-linked two-to-eight-scene CPU composition from hash-bound owner-local PCM narration, exact frame-boundary padding, original board rendering, H.264/AAC MP4, scene-level WebVTT and output manifests.
- 24 synthetic two-scene English eSpeak demonstrations for the 12 domains and two formats; explicit nonpublication status, no factual or professional voice acceptance.
- Explicit boolean rights self-attestation, unsafe path/tamper/format checks, duration limits, output no-overwrite and caught-failure cleanup. Added focused tests and operator CLI/guide.
- No owner account, suspended remote, external models or production data accessed.

## 2026-11-24 Phase 7 — reconstructed domain storyboard drafts

- Source-linked, fail-closed ASCII storyboard contracts for all 12 domains and both formats; original illustrative PNGs and optional silent 3-second FFmpeg animatics.
- 24 synthetic demonstration pairs, source declarations and hash-bound manifests; no factual, rights or publication acceptance.
- Operator CLI, adversarial tests, Windows portable test coverage and updated recovery tracker. No account access, owner-data changes or automatic publishing.

## 2026-11-24 Phase 6 — MP4 narration conformance and localhost browser isolation

- Added bounded first-audio-track FFmpeg decode + distributed sampled PCM correlation against owner-reviewed narration WAV; wrong-track swaps now block bilingual delivery, even if MP4 hash and FFprobe metadata were updated. This is a conservative signal comparison, not speech recognition or professional review.
- Added same-origin/loopback HTTP guard to protect the local app from off-host Host requests, cross-site forms, browser Origin abuse and basic DNS rebinding. The bundled synthetic TestClient smoke opts into synthetic test host explicitly.
- Added adversarial regression tests and included local host guard in Windows CI contracts.
- Continued retaining all earlier source snapshots and recovery artifacts. Real OAuth, actual licensed models, target Windows PC and expert rights reviews remain external blockers.

## 2026-11-24 — Phase 5: private owner acceptance evidence (NOT external acceptance)

- M2.4: offline hash-bound two-person native-language listening self-attestation against an actual local Piper WAV draft, with technical QA and no reviewer notes exposed in output. **Identity, rights, quality and listening are not independently authenticated.**
- M2.5: exact local SHA-256 audit of distinct Hindi and English script, captions, narration WAV, H.264 video, rights metadata and listening receipt, with no publishing authorization. Fail-closed SRT cue structure, chronological timing and per-video duration checks; narration review `text_sha256` must match exact localized script bytes. Video audio identity remains unproven by this technical audit.
- M3.2: offline binding of existing owner OAuth read-only PRIVATE-video report, channel/video identity hashes, Analytics-observed state and human Studio checklist; it cannot authenticate API data or perform account write actions.
- Operator CLIs are no-overwrite and private by default; separate Windows contract tests; actual models, owner Windows machine, Google OAuth and private upload remain external/blocked acceptance dependencies.
- Only **new-repository** development is performed. Unavailable 13–20 Nov source history remains unrecovered.

# ViralOS Engineering Changelog

## 2026-11-24 — Phase 4 (recoverable owner-local voice)

- Added owner-supplied Piper CLI *actual subprocess* synthesis adapter, with SHA-256 model/config/binary checks, strict rights attestation, bound input/timeout/output, FFmpeg 16kHz PCM conversion and listening-required reports; no model bundles or network downloads.
- Added optional owner-confirmed scene-cue retimer for M2.5 localized CPU previews, with measured WAV duration, unchanged owner subtitle timestamps and fail-closed validation.
- Added contract, error, tamper and FFmpeg integration tests plus operator guide. No natural voice, automatic dubbing, owner Windows install, rights clearance or real YouTube acceptance claimed.

# ViralOS engineering changelog

## 2026-11-24 — Phase 3: acoustic-model proof and no-duplicate private reconciliation

- M2.4: strict offline CTC model inventory with byte-level SHA-256 of all model files, owner license/locale attestation and fail-closed CLI requirement. Model inference stays optional and **unverified without owner model**.
- M2.4: real-reference word-timing diagnostic over caller-provided corpus (median/p95 boundary error, mismatches, minimum sample-size guard); never auto-certifies model, speech quality or voice rights.
- M3.2: owner-supervised read-only recovery of REMOTE_UNKNOWN video into UPLOADED_PRIVATE on exact authenticated/private/channel/metadata match, append-only event table migration 013; no blind retry, new upload or publication acceptance.
- M4: refuse NTFS alternate streams and reserved device names in backups, reject unsafe ZIP types and delete failed backup snapshots.
- All prior code, recorded history, manual approval boundaries, rights checks and original archives remain preserved.

## 2026-11-24 — Phase 2: safe-release gate and real localized technical preview

- PRIVATE upload execute is blocked until **current M2.6 owner/editorial attestation**, with a read-only, no-network readiness endpoint. No automatic retry or public publishing.
- M25: approved human locale variant + owner-supplied WAV + exact matching localized shot text and owner-timed captions can render a real watermarked CPU MP4 technical preview with file provenance, technical QA, stale dependency/file-hash validation; SQLite migration 012, including stored owner voice provenance. Hindi preview rejects unverified Latin-only font fallback. No generative TTS, auto-translation or owner final release approval.
- Added disposable SQLite/outputs backup/verify/restore acceptance drill and Windows owner-run local acceptance script. This does NOT validate real user data/physical hardware by itself.
- Added Windows CI Python-contract and PowerShell-syntax job using independent synthetic databases (no workflow-level runner-context expression), plus read-only 12-domain/24-film source/rights/video acceptance checklist (all initially pending).
- No old suspended account accessed, real YouTube account contacted, copyrighted footage acquired or external models downloaded.

## 2026-11-24 — Additional offline, human-gated capabilities

- Domain adapters: twelve differentiated domain-specific evidence metadata checkers, not generative agents.
- Localization M25: immutable Hindi/English/Hinglish draft plus glossary/on-screen metadata, source and number review; SQLite migration 010.
- Editorial M26: read-only evidence/license audit and nonlegal owner attestation bound to current valid M2.2 final export; SQLite migration 011.
- Owner backup: no-network, read-only reconciliation of local ZIP/folders; detects migration conflicts and ignores credential paths.
- Compute: explicit CPU-first routing contract and model-license/VRAM preflight. GPU inference and dispatch not implemented.
- Audience: noncausal retention-to-scene mapping of supplied data with sample-size/source caveats, no revenue forecast.
- Existing M2.4 CTC and M3.2 read-only acceptance code preserved; no real account actions or external model downloads.

## 2026-11-23 — M2.4 and M3.2 reconstruction increment

See `docs/M24_M32_ENGINEERING_HANDOFF.md` and prior Git commit. Earlier 12 November source and package snapshots remain archived in `recovery/original-artifacts/`.
