# Phase 14M — Hindi owner assembly, declared timing and production preflight (2026-11-25)

Base: 5083e335dd8108d56fefa636be3b74b9dc98d15b; [Phase 14L CI run 45482666390](https://github.com/mohdazizshaikh/youtube/actions/runs/45482666390) initially running, subsequently verified successful. Draft PR #7; main stays at Phase 13. Three workstreams implemented; no account access, production DB change, external model download or publication authority.

## Evidence and limitations

- Hindi owner-path assembly validates the existing 24-shot owner recording/local TTS manifest, exact input SHA256, original per-shot script/WAV hashes, PCM format and actual sample counts. Uses fresh frame rounding and zero padding, two parallel encoders, shaped static boards, separate shot-index progress lane, no unverified captions. Artificial fixture only: 24 identical 440Hz tone WAVs of 144001 samples each, explicit test declarations, persistent ARTIFICIAL PCM TEST / NO SPEECH / NO RELEASE marking. Full render 2184 frames, 72.8s, native 1920x1080/30fps H.264/AAC, both streams 72.8s, complete decode passed. Render+audit 26.72s isolated Linux. Video SHA256 6538208653fe4387f2d4050ccba4d2c24d866cd756e829da085b6d5b8b1c1cd3; assembled WAV c065ec28c9b1fdd7807b0db2bf366a31a9a92ee782cadfaafd1f03ea0f8b6fe6; fixture manifest ae31638786cfd856759774891d132ee9d2e297acf242ea7402574f81e1da995d. Numeric audio gate failed (-30.60 LUFS/-25.85 dBTP, LRA 0). No tone mastering attempted; prior bilingual synthetic films unchanged. Not real speech, cinematic animation or human review.
- Declared reviewed timing compiler supports en-US retime assets and hi-IN owner manifest/assets, externally pinned timing manifest and source identity, exact 24 shot/script/WAV hashes and exact whitespace token coverage. Integer sample boundaries are non-overlapping, at least 1920 samples (40ms) and inside actual PCM, with inward centisecond rounding, global frame offsets including padding, at most four words per group and width measurement. Output ASS and global word JSON pinned in receipt. Compiler does not perform CTC inference or validate independent annotators, model identity, semantic speech correspondence or rights. Explicit owner_reviewed_manual/owner_reviewed_ctc declarations are not verified evidence; independent benchmark and review remain mandatory. Hindi artificial fixture compiled 772 words, 2184 frames; timing SHA256 80fc05dbc3eff5938fd71f2805ba28accce706d9ae7d57d844fed34b596d770e, ASS a6bdbb22cd18f5755e1aac0e582672fdba580350b6b37e1ba26f80d8e4d101f7, words dd4d1523d1f7a10211dfce9e3e453b3180e706763dbffdf5917f3b725cd38658. English contract tested with small artificial tokens, not a full English owner caption compile. Artificial timing explicitly labeled using --fixture. Six-second Hindi caption overlay decoded, 180 frames at 1080p/30fps; one sampled frame inspected. Warning text is close to the progress lane; no full-length caption burn-in, caption reading-speed validation or all-scene visual review.
- Read-only environment preflight reports OS, Python, installed package versions, ffmpeg/ffprobe version, H.264/AAC encoder and ASS filter presence, RAQM and local font load. Actual Linux Python 3.13.5, FFmpeg 7.1.5, Pillow 12.3.0, RAQM/ASS/encoders present, FreeSans and DejaVu Sans load. Piper not present; eSpeak present. Detection is not a font glyph coverage test, real model inference, Windows installation, browser acceptance or resource benchmark. No installation or downloads. No physical owner hardware.
- 19/19 new and 88/88 combined Phase 14I–M local tests passed (3.14s). Four source/test Git blobs matched local tested bytes. Full Git checkout previously DNS-blocked; not re-tested here. Personal Library copies of four source/test files used for transfer; no private audio or rights data committed. Latest Phase 14M integrated CI pending after manifest refresh.

## Reproduction

Use trusted local Python, Pillow/RAQM and FFmpeg with libass. Fresh owner-controlled private directories outside source. Keep INCOMPLETE failures. Never commit recordings, model/license records or reviewer evidence.

    python -m tools.phase14_preflight --fontpath <local-mixed-font> --latinfont <local-latin-font> --output <new-preflight.json>
    python -m tools.phase14_hindi_owner --plan tools/phase14_hi_plan.json --manifest <owner-manifest.json> --assets <private-wavs> --expected <manifest-sha256> --output <new-hindi-review> --fontpath <local-mixed-font> --latinfont <local-latin-font>
    python -m tools.phase14_reviewed_timing --locale hi-IN --plan tools/phase14_hi_plan.json --source <owner-manifest.json> --assets <private-wavs> --expected <manifest-sha256> --timing <reviewed-timing.json> --timing-sha <timing-sha256> --output <new-caption-dir> --fontpath <local-mixed-font>
    python -m tools.phase14_reviewed_timing --locale en-US --plan tools/phase14_film_plan.json --source <retimed-folder> --expected <retime-receipt-sha256> --timing <reviewed-timing.json> --timing-sha <timing-sha256> --output <new-caption-dir> --fontpath <local-latin-font>
    python -m pytest -q tests/test_phase14_reviewed_timing.py tests/test_phase14_owner_assembly.py tests/test_phase14_workspace.py tests/test_phase14_bilingual.py tests/test_phase14_localize.py

Timing JSON: exact keys schema VIRALOS_REVIEWED_WORDS_V1, locale, source_sha256, basis owner_reviewed_manual or owner_reviewed_ctc, timing_review_attested true, shots array (24 ordered records with zero-based shot, wav_sha256, script_sha256, words). Each word record has text, start_sample, end_sample (integer offsets in original unpadded PCM at 48kHz). Provide a real independently reviewed manifest only after actual speech verification; --fixture is only for explicit artificial test evidence, never use artificial timing as real. Word count and timestamp validity are not acoustic accuracy. Keep actual benchmark evidence from Phase 14H. Compile output is private review input, not a release or verified aligned-caption status. Test overlay was a manual FFmpeg ASS burn-in of the first six seconds; no new integrated caption-video assembler yet.

## Current priorities

| Priority | Gate | Status / next proof |
|---|---|---|
| P0 | CI/package | Phase 14L green; Phase 14M manifest refresh/latest CI pending |
| P0 | Bilingual owner assembly | Both English and Hindi fixture-rendered; actual licensed narration absent, real full films pending |
| P0 | Natural voice runtime | Pinned adapter contract tested; Piper absent, licensed models/inference/native listening pending |
| P0 | Real acoustic alignment | Benchmark available; actual model inference and independent bilingual reference annotations pending |
| P0 | Genuine captions | Reviewed timing contract compiler tested; Hindi artificial 772-word cues and 6s overlay; actual speech timing and integrated full-film burn-in pending |
| P0 | Creative | Static Hindi boards and shot-index lane; differentiated semantic animation, warning-lane spacing and complete human watch-through pending |
| P0 | Audio | Prior synthetic films passed numeric gates; new tone fixture fails, real audio mastering/listening pending |
| P1 | Deployment | Read-only Linux preflight tested; actual Windows dependency/setup and browser acceptance pending |
| P1 | Editorial/packaging | Private synthetic bilingual workspace and drafts; independent factual/native/rights review, new real-media adapter pending |
| P1 | Recovery | Synthetic isolated restore passed previously; physical owner restore pending |
| P1 | YouTube | BLOCKED_OWNER_AUTHORIZATION; no live account, private upload or analytics |
| P2 | Optimization | 26.72s isolated Hindi artificial fixture; owner PC CPU/RAM/disk/cost unmeasured |
| Recovery | 13–20 Nov source | BLOCKED_OWNER_BACKUP |
| Release | Merge | OPEN; latest CI, owner/editorial acceptance; main preserved |

Next: prioritize real voice and actual reference annotations rather than further artificial media; implement hash-bound caption burn-in with review-only output, distinct motion graphics, audio/visual perceptual QA and physical Windows acceptance. See [project status](PROJECT_STATUS.md) and [owner acceptance checklist](OWNER_ACCEPTANCE_2026-11-25_PHASE14J.md). No synthetic release, public publishing or 12-domain expansion.
