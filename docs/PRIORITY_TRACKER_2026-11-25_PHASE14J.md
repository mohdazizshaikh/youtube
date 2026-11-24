# Phase 14J — bilingual review films, English owner intake and acceptance handoff (2026-11-25)

Base: 58a7420c014e7fa93b7dffa310b27a97c125cf3e; [Phase 14I integrated CI run 45464050233](https://github.com/mohdazizshaikh/youtube/actions/runs/45464050233) passed. Draft PR #7, main remains Phase 13. Multiple workstreams executed; no external model downloads, real account access, production database changes or publication authorization.

## Executed evidence

- Restored all 24 Hindi board PNGs deterministically using the Phase 14I plan and original local FreeSans/DejaVu font environment; every original board hash matched. Input receipt SHA256 01488dfcd616d1692e17b48f4090da3dc7ebac34f2302b11caeb02b12a52958c, plan eaf1eefbe8b4ff920297a3adc9a2c289fdfe9adacd6e7f67dad69237d89042a9, assembled synthetic PCM WAV 65482c237d3a75a76cb0f949d1232813ed171119e326cdd61245d716c3ea84be. Intake validates receipt pin, ordered timeline, PCM format/length, per-shot nonzero samples and exact zero padding. The declared original segment WAV hashes are not independently reverified against individual files in this render; only assembled WAV and receipt bytes are pinned.
- Rendered full Hindi film with two parallel FFmpeg shot encoders: eight chapters, 24 static educational boards, 772 synthetic word cues, 1920x1080/30fps H.264/AAC, 9829 reported video frames and 327.633333s duration. 116.49s isolated Linux render and audit. Original static boards scaled to 1632x918, warning and caption strips separated. Width-checked groups up to four words, equal-distribution artificial centisecond timestamps, persistent warning. Eight decoded chapter frames inspected; mixed-script shaping and highlighting visible. No continuous scene-specific animation, acoustic alignment, natural speech, complete human watch-through or native editorial certification. Duration remains below 6–8 minute original target.
- Raw Hindi video SHA256 88b575941be4ccb22a9abf736f6b49d854af871e59c3427440e122d3f0d1a118; word timeline SHA256 928f5fd4c18cc3645d70c6d9fea1c5d4e52ecb58621fea6e01a2ff7331d19605; raw receipt SHA256 35b8d997500d7ba9a44d2cb52b4ff937525cc0d76fdd8a61b8e6a887088c8684. Full decode passed. Reused Phase 14B mastering first candidate: -19.78 LUFS/-1.03 dBTP to -16.85 LUFS/-1.38 dBTP (LRA 1.6 LU). Mastered SHA256 6a849cd4b826e7018da969304378d987096832ef3d836f77581997a9a393a7af; fresh final audit: 9829 frames, video 327.633333s, audio 327.637s, full decode and numeric audio gate pass. Independent listening remains pending.
- Bilingual packaging draft V2 preserves existing English metadata/thumbnail declarations, binds the actual Hindi mastered SHA and eight chapter start timestamps derived from Hindi intake, and embeds fresh final technical audit. Metadata SHA256 327329762b9e5fb578fa84b5afec8f0d2f2e1a7e56f7863ba37d31848bed230c. Hindi chain validated; English packaging is inherited from Phase 14I and not freshly audited by this binding function. No upload authorization or CTR claim.
- New owner English chapter intake/request kit with eight exact original scripts, intentionally incomplete manifest, private rights/listening declarations, safe names and PCM16 mono 48kHz 1–90s/hash validation. Tested only with artificial WAV fixture; real speech verification, shot segmentation and owner-audio rendering pending. Hindi synthetic renderer deliberately rejects owner basis; no old synthetic captions may be reused for real voice. Owner declarations are not independent rights proof.
- 19/19 new isolated tests and 37/37 combined Phase 14I/J tests passed. Source/test Git blobs match local tested bytes. Full checkout DNS failure reproduced. Latest integrated CI and package verification pending; prior Phase 14I CI green. No changes to existing review database or release gates.
- [Owner acceptance checklist](OWNER_ACCEPTANCE_2026-11-25_PHASE14J.md) created for physical Windows, trusted setup, bilingual voice, independent real alignment, native watch-through, browser, backup/restore, hardware resource logs and separately authorized private-account evidence. All owner gates remain pending.

## Reproduce

Use trusted Python/Pillow with RAQM, FFmpeg/ffprobe with libass, local original fonts/runtime, and Phase 14I prepared private folder. Fresh private output paths, no private recordings or rights records in Git. INCOMPLETE marks failed runs; source file hashes must match. For synthetic-only review:

    python -m tools.phase14_bilingual render --plan tools/phase14_hi_plan.json --folder <hi-prepared> --expected <intake-receipt-sha256> --output <new-hi-review> --fontpath <original-mixed-font> --latinfont <original-latin-font>
    python -m tools.phase14_quality master <hi-review>/hindi_review.mp4 <new-mastered> --sha256 <actual-review-video-sha256>
    python -m tools.phase14_bilingual bind-metadata --draft <packaging-v1-json> --hi-plan tools/phase14_hi_plan.json --folder <hi-prepared> --expected <intake-receipt-sha256> --raw-video <hi-review>/hindi_review.mp4 --render-receipt <hi-review>/receipt.json --mastered <mastered>/mastered.mp4 --master-receipt <mastered>/receipt.json --output <new-metadata-json>
    python -m tools.phase14_bilingual english-request --plan tools/phase14_film_plan.json --output <new-owner-kit>
    python -m tools.phase14_bilingual english-intake --plan tools/phase14_film_plan.json --manifest <owner-manifest> --assets <owner-assets>
    python -m pytest -q tests/test_phase14_bilingual.py tests/test_phase14_localize.py

## Consolidated priorities

| Priority | Gate | Status / next proof |
|---|---|---|
| P0 | CI/package | Phase 14I green; Phase 14J manifest refresh and latest CI pending |
| P0 | Bilingual full-film technical drafts | English V6 373.633s, Hindi 327.633s; full decode and numeric mastering passed; synthetic only |
| P0 | Natural bilingual voice | Both owner intake contracts ready; BLOCKED_OWNER_MODEL_OR_RECORDING; actual licensed assets and native listening required |
| P0 | Real alignment | Phase 14H evaluator tested; real CTC inference and independent bilingual reference annotations pending |
| P0 | Captions | English/Hindi synthetic full-film cues rendered; actual speech timing and human readability review pending |
| P0 | Creative | Hindi static boards; English progress-lane animation; differentiated scene-specific animation and factual review pending |
| P0 | Voice replacement assembly | English eight-chapter intake and Hindi 24-segment intake ready; actual owner-speech retime/render not integrated |
| P1 | Bilingual packaging | Draft V2 both video identities/chapter lists; native review and actual CTR pending |
| P1 | Editorial | English versioned API tested previously; Hindi schema adapter, actual browser playback and human revisions pending |
| P1 | Windows/recovery | Owner checklist ready; physical install, playback, restore and resource logs pending |
| P1 | Authorized YouTube | BLOCKED_OWNER_AUTHORIZATION; no real private upload or analytics |
| P2 | Optimization | 116.49s isolated Hindi render+audit; physical CPU/RAM/cost unmeasured |
| Recovery | 13–20 Nov source history | BLOCKED_OWNER_BACKUP |
| Release | Merge | OPEN; latest CI, review and acceptance; main preserved |

Next parallel batch: versioned Hindi/bilingual editorial adapter; real owner voice/CTC runtime if assets available; differentiated motion design and factual review; owner Windows/browser and restore evidence. No synthetic release, public publishing or 12-domain expansion until single-channel acceptance. See [project status](PROJECT_STATUS.md).
