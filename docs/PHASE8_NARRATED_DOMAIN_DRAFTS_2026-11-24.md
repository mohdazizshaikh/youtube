# Phase 8 — Local narrated domain drafts

Base: new repository `0319199a378e4d8f8e47053e03f4f9ca0bf29b51`. Phase 7 source preserved. No account or network actions are performed by the composer.

## Reproduce the synthetic demonstrations

Install repository Python requirements, FFmpeg/ffprobe (libx264 and AAC support), and local eSpeak/eSpeak NG. From the repository root:

```powershell
python -m tools.domain_draft_demo --output-dir outputs/narrated-demo-v1
```

Use a new directory with an existing parent. The demo generates 24 synthetic English narrated clips, two scenes each, for 12 domains and both portrait/landscape. They contain explicit NOT FACT / RIGHTS CLEARED visual watermarks and intentionally no real claims. English eSpeak is a basic synthetic demonstration, not natural voice or commercial-license certification. The pack contains source declarations, narration inputs, boards, MP4, concatenated WAV, sidecar captions and per-draft manifests. Never upload demo artifacts to a real channel as accepted videos.

## Compose an owner-local draft

The demo's `draft/plan.json` is a concrete schema example. Prepare 2–8 valid Phase 7 storyboard scene objects, with consistent domain, format and demo classification. For each scene provide a distinct safe leaf WAV filename under the asset directory, its exact lowercase SHA-256, intended narration text, and explicit boolean rights self-attestation. WAV must be mono 16 kHz PCM16, 0.5–30 seconds per scene, with a nonzero sample. Keep actual scripts and evidence private and outside Git.

```powershell
python -m tools.domain_draft_video --plan outputs/narrated-demo-v1/sports_short/draft/plan.json --assets outputs/narrated-demo-v1/sports_short/assets --output-dir outputs/another-draft
```

The tool validates the source-linked storyboard contracts and input bytes, pads each scene to the next 25 fps frame boundary (40 ms), generates original illustrative boards, concatenates PCM, and encodes H.264/AAC with FFmpeg. Draft limits: 60 seconds portrait; 120 seconds landscape. FFprobe checks frame count, dimensions, track presence and duration. Scene-level WebVTT captions are escaped plain text, not automatic word-level alignment or embedded captions. Inspect the sidecar with a suitable player; it is not burned in. Manifests bind all output files other than the manifest itself, plus input WAV hashes, board declarations and padded PCM scene hashes. Existing output directories are never overwritten; on a caught render failure the newly created output is removed. No external media inputs, source fetch, OAuth or upload. Use a private trusted local workspace; the tool does not defend against a malicious process with simultaneous filesystem access.

## Limits and acceptance

Source/rights attestations are self-declarations, not independent verification. Storyboard title/claim graphics remain ASCII-only. The renderer does not prove factual accuracy, naturalness, correct spoken words, speaker identity, complete audio-waveform conformance, rights clearance, full creative autonomy or monetization. Full speech/word-level benchmarking, bilingual review, target physical Windows performance, authorized real YouTube PRIVATE acceptance, verified real source data, domain specialists, GPU models and analytics remain outstanding. All manifests have `publication_eligible: false`.
