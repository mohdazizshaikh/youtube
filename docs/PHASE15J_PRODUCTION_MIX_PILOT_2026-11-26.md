# Phase 15J — pinned production mix derivative

Phase 15I candidate 20b1157c1090ff23b4d27c6556386a4c0e3a4cc4, CI 45697364882: Linux 999 passed, 788 hashes verified; hosted Windows 876 passed, 57 skipped. New Phase 15J CI pending; hosted CI is not owner acceptance.

## Operator workflow
Stop consoles and preserve the parent and trusted manifest pin. The new derivative accepts one original stopped pilot run (ASCII or native Hindi), a separately pinned exact-length owner-local music WAV, and a pinned mix request. Parent narration master is the source voice; a parent already declaring a production mix is rejected. A native parent's font provenance must be independently verified with native_hindi_pilot; this module audits the pinned child media only. Original voice, source evidence, board PNG bytes and captions retained in the parent; mixed child has distinct scene WAVs and a separate PENDING queue. No existing output overwritten.

Request fields: schema VIRALOS_PRODUCTION_MIX_REQUEST_V1, parent_manifest_sha256, mode STATIC or DUCK, audio_request (full Phase 15H static mix or Phase 15I duck request). The nested voice_sha256 must match the parent's actual narration.wav SHA-256; music_sha256 and self-attested rights are mandatory. Exact-length 3–120s 16k mono PCM16; each scene split at existing 25fps frame boundaries. No resampling, trimming, looping or external media retrieval. New plan binds parent manifest, original narration and boards, request, mixed master and music pins as reserved specialist declarations; the default renderer rejects such declarations. Existing generic renderer path unchanged.

```
python -m tools.production_mix_pilot build --parent /private/parent-run --parent-sha256 PARENT_PIN --music /private/music.wav --request /private/mix-request.json --request-sha256 REQUEST_PIN --output /private/mixed-run
python -m tools.production_mix_pilot verify --parent /private/parent-run --parent-sha256 PARENT_PIN --music /private/music.wav --request /private/mix-request.json --request-sha256 REQUEST_PIN --output /private/mixed-run --mix-sha256 MIX_PIN
```

Output: run/ (normal pilot child) and mix.json (independent pinned derivative receipt). Existing per-child console and snapshot accept run/ with its own manifest pin; preserve parent, music, request and outer receipt separately. No combined bilingual mix snapshot yet. Fresh verify recomposes the exact mixed PCM, validates every scene asset, unchanged PNGs/captions/timing, and fresh existing media audit. Also measures FFmpeg-decoded AAC at 16k PCM and rejects measured true-peak ceiling breaches. Decoded-rate diagnostic is not codec-native-rate true-peak certification. FFmpeg measurement version changes can require a new candidate; never bypass byte verification. No independently validated music rights, intelligibility, professional mix, real voices, native visual acceptance, or publishing. Localized diagrams and motion graphics remain pending. New CI pending.
