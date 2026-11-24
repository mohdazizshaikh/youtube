# Phase 9 — independent technical media audit

Base: `dd3e2cc74e70b977fc87a118bd34a2e8698b51cf` in `mohdazizshaikh/youtube`. Original suspended remote was not accessed.

The composer uses fixed 25 fps timestamps after scene concatenation and a duration limit rather than stopping video at a frame count while AAC still needs flushing. It checks video and audio duration, frame count and frame rate. This fixes short-scene narration truncation found by an independent decoded-media test.

The offline auditor requires a **previously retained, trusted SHA-256 pin** of `draft/manifest.json`, original narration assets, and exact expected draft inventory. It reconstructs padded PCM and scene captions from the plan and validates source declaration, file, timing, and scene hashes. FFprobe checks streams, dimensions, frame count and duration; FFmpeg decodes actual narration and samples each scene midpoint, comparing it to the declared storyboard PNG. Each scene's waveform comparison uses bounded correlation, coverage and offset thresholds. The report remains nonpublication-eligible. A manifest pin is not a digital signature; a pin generated from a substituted bundle is not independent provenance. A sampled signal comparison cannot prove every frame, spoken word, or speaker identity. Self-attestation does not certify license, consent, factual accuracy or legal rights. Use a trusted private workspace without concurrent untrusted writers.

Run from repository root with Python dependencies and FFmpeg/ffprobe available:

```powershell
python -m tools.domain_draft_audit --draft outputs/narrated-demo-v2/sports_short/draft --assets outputs/narrated-demo-v2/sports_short/assets --manifest-sha256 YOUR_PREVIOUSLY_RETAINED_MANIFEST_SHA256 --report outputs/sports_short-audit.json
```

The report path must be new and outside the audited draft inventory. Keep owner material private. To regenerate synthetic demos and their technical audits:

```powershell
python -m tools.domain_draft_demo --output-dir outputs/narrated-demo-v2
```

The demo requires local eSpeak and creates synthetic English clips, not accepted films. `index.json` binds manifests, MP4s and audit reports. Tests reject missing/extra files, altered captions/timing, changed inputs, mismatched pins, publication flag manipulation, and actual wrong audio/visuals even after rehashing. Full local suite: 228 passed; hosted CI does not replace real owner hardware validation. See Phase 9 tracker for real model, account, device and editorial blockers.
