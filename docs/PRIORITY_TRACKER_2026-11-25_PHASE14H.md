# Phase 14H — parallel editorial studio, visual polish and alignment benchmark (2026-11-25)

Base 19bdc1ec70a3c3579fb4d172cfe6c4cb05c7cf22; [Phase 14G integrated CI run 45459133731](https://github.com/mohdazizshaikh/youtube/actions/runs/45459133731) succeeded. Continue draft PR #7; main remains Phase 13. Three parallel workstreams executed; no account access, model downloads, production DB migration, legacy queue approval or publication authorization.

## Executed evidence

- Visual polish: regenerate all 24 boards from pinned English plan, with two parallel shot encoders, board rectangle (144,0,1632,918), motion lane (144,930,1632,32), caption strip (0,972,1920,108). Moving dot stays outside board; removed overlay focus rings. Full 373.633333s 1920x1080/30fps 11209-frame synthetic review video; 130.24s render+audit on isolated Linux. Eight decoded chapter midpoints visually checked. Board smaller than V5; motion primarily progress lane, not semantic/cinematic animation. Full human readability, timing and listening review pending.
- V6 SHA256 ebbbd504895d54472a127492efeb647037a57e132bdef84858d2aef7a19fc50d, 22536166 bytes vs V5 53965484 bytes; content differs so not a compression quality benchmark. AAC payload SHA256 052a7cfecabcd2bb1ddeb7a33b2c78e3a70839117621aadccd6d942d612d8448 preserved. Fresh full decode, numeric gate -16.73 LUFS/-1.39 dBTP, 1.8 LU LRA passed. Caption timing remains synthetic and warning retained.
- Versioned separate Phase 14 editorial workspace: pinned video, receipt and timeline; staged exact bytes and fresh audit; SQLite application ID/schema and workspace pin; bounded, append-only time-coded issue notes with revision CAS; localhost-only CLI with session token, Host/Origin/fetch-site checks and CSP; browser UI with chapter navigation, player and issue categories. No approval endpoint or export authority. Existing Phase 13 app/queue unchanged. In-process actual ASGI TestClient verified exact video bytes for both V5 and V6, submitted automated notes, rejected stale revisions (409) and verified persistence across new app instances. V6 workspace has one automated note, not human acceptance. The actual headless Chromium navigation attempt failed ERR_BLOCKED_BY_ADMINISTRATOR, so browser playback/seek/UI acceptance is OPEN; do not bypass environment policy. Review notes are private local text, not encrypted; owner-controlled filesystem assumed. Serve holds verified video in memory (128MB cap), not production-scale streaming. API guard is not protection against hostile local processes. Source receipts are declarations, not authenticated provenance.
- Alignment evaluator: compare manual reference vs CTC candidate declared word boundaries for same pinned script/WAV; exact token count, timestamp bounds, distinct manifest hashes, locale, declared rights/listening/independent reference/model SHA checks; median and nearest-rank p95 over start and end absolute errors, thresholds <=80ms and <=200ms. Synthetic fixture with 28 words/56 boundaries and intentionally shifted 30ms timestamps yields median/p95/max 30ms; this is arithmetic verification only. Real CTC inference, independent annotator verification and actual natural bilingual speech remain blocked. Minimum 20 words is intake floor, not a sufficient full-film acceptance sample.
- 17/17 new isolated tests passed, rerun passed. All four new source/test Git blobs exact match local bytes. Full checkout DNS blocker persists from previous increments; latest integrated CI and manifest verification pending. No real account actions or release authority.

## Reproduce

Trusted Python, Pillow, FFmpeg/ffprobe (libass, libx264/AAC), local TrueType font, FastAPI/uvicorn. Choose fresh output directories under private owner-controlled storage, outside repository. Never commit private media, notes, license or credential data. INCOMPLETE means failed run. No downloads by tools.

    python -m tools.phase14_visual_polish --plan tools/phase14_film_plan.json --timeline /private/motion/receipt.json --review /private/v5/captioned_review.mp4 --receipt /private/v5/receipt.json --ass /private/v5/review.ass --output /private/v6 --font /path/to/DejaVuSans.ttf
    python -m tools.phase14_editorial prepare --video /private/v6/polished_review.mp4 --video-sha <actual-video-sha> --receipt /private/v6/receipt.json --receipt-sha <actual-receipt-sha> --timeline /private/motion/receipt.json --timeline-sha <actual-timeline-sha> --output /private/review-v6
    python -m tools.phase14_editorial serve --workspace /private/review-v6 --port 8766
    python -m tools.phase14_alignment_benchmark --script /private/shot.txt --wav /private/shot.wav --reference /private/manual.json --reference-sha <actual-reference-sha> --candidate /private/ctc.json --candidate-sha <actual-candidate-sha>
    python -m pytest -q tests/test_phase14_editorial.py

Open http://127.0.0.1:8766/ only on the owner machine; record real playback and seek evidence, not assumed. For synthetic arithmetic test use --synthetic only with both manifests explicitly synthetic. For actual evaluation provide owner-reviewed manual/CTC manifests with rights_attested=true, listening_attested=true, private rights_reference, reference independent_reference_attested=true, candidate model_sha256. These are declared fields only, not legally or independently verified. No acceptance or authorization from numeric benchmark alone.

## Consolidated priorities

| Priority | Gate | Status / next proof |
|---|---|---|
| P0 | CI/package | Phase 14G green; Phase 14H refresh and latest integrated CI pending |
| P0 | Visual overlap | MOTION_LANE_FULL_FILM_TESTED; source board/marker separation and eight sampled frames; full watch-through, readable scaling and differentiated animation pending |
| P0 | Natural English/Hindi voice | BLOCKED_OWNER_MODEL_OR_RECORDING; licensed speech, native review, pronunciation |
| P0 | Acoustic alignment | BENCHMARK_IMPLEMENTED; synthetic arithmetic pass only; real CTC inference and manually annotated multilingual representative evidence |
| P0 | Animated captions | Full synthetic V6 rendered; real speech timings and Hindi typography review pending |
| P0 | Story | Original 932-word English script; independent factual/pacing review, native Hindi adaptation pending |
| P0 | Audio | NUMERIC_PASS_AAC_PRESERVED; licensed speech and listening review |
| P1 | Private editorial console | VERSIONED_SEPARATE_WORKSPACE_API_TESTED; actual browser blocked by environment; no legacy queue registration, no production integration/approval |
| P1 | Time-coded revision tracking | SQLite append and stale rejection plus restart persistence tested; actual owner revisions/human review pending |
| P1 | Thumbnail/title | Draft only; professional original packaging and review pending |
| P1 | Rights/editorial | BLOCKED_HUMAN_REVIEW; no synthetic release |
| P1 | Windows/browser/restore | BLOCKED_OWNER_HARDWARE; browser environment restriction documented |
| P1 | Authorized YouTube | BLOCKED_OWNER_AUTHORIZATION; no live upload or analytics |
| P2 | Resource optimization | Parallel visual encoders and 130.24s isolated benchmark; owner PC CPU/RAM/cost unmeasured |
| Recovery | Missing 13–20 Nov source history | BLOCKED_OWNER_BACKUP |
| Release | Merge | OPEN; reviewed integration, latest CI, owner acceptance; main unchanged |

Next: actual licensed bilingual narration and independent alignment evidence, complete native-speaker review, real owner Windows/browser run, final thumbnail and truthful metadata, then versioned integration under original private release gates. Do not approve synthetic media or expand into 12 domains until single-channel pilot acceptance. See [project status](PROJECT_STATUS.md).
