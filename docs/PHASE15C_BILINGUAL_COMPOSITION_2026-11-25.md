# Phase 15C — bilingual audio composition and scene captions

Previous verified commit e3670b1e6a4f018fbdbcce2273b1cb4c83c7822a, CI 45647974382: Linux 563 passed, 753 package hashes; Windows 451 passed, 46 skipped, PowerShell passed. New increment pending its own CI.

Uses Phase 15B timing request unchanged plus independently pinned captions JSON:
schema VIRALOS_BILINGUAL_SCENE_CAPTIONS_V1, timing_request_sha256 (exact timing request bytes), scenes array matching the timing request; each row has scene integer, hindi and english strings. Captions are single-line 3–500 characters, checked for script mix and control/markup injection. Text is escaped in WebVTT, not interpreted as markup. Script checks are heuristic, not linguistic verification.

```
python -m tools.bilingual_compose compose --root /private/inputs --request /private/timing.json --request-sha256 TIMING_PIN --captions /private/captions.json --captions-sha256 CAPTION_PIN --output /private/bundle
python -m tools.bilingual_compose verify --root /private/inputs --request /private/timing.json --request-sha256 TIMING_PIN --captions /private/captions.json --captions-sha256 CAPTION_PIN --bundle /private/bundle --manifest-sha256 TRUSTED_BUNDLE_PIN
```

Composition refuses any timing review flags. Creates two separate 16kHz mono PCM16 master tracks, per-scene padded WAVs (hindi_01.wav etc.), two scene-level WebVTT files and deterministic manifest. Exact input PCM retained; zero-padding only, no speed, trimming, synthesis, normalization or mixing. Both masters have equal length and align to 25 fps boundaries. Captions cover the entire scene including padding, not actual word timing. Manifest records source and padded PCM hashes, per-scene timing, caption text pins and all file hashes. Fresh verification recomputes exact expected bytes from the original pinned inputs and rejects any missing, extra or modified output. Keep pins separately. No overwrite; incomplete write retains marker. Use a new private sibling output outside source and inputs. Output contains private narration and script content; do not commit or sync publicly. Use owner-controlled quiescent storage; not encrypted, not hostile-concurrency-safe.

Per-scene WAVs can be used as inputs to the existing pilot builder after creating distinct localized storyboard plans with matching narration hashes, captions and owner rights declarations. This step is manual; a complete bilingual video render, licensed TTS, CTC alignment, loudness/true peak mastering, translated claims/graphics and owner listening remain pending. No publication authorization or live account operations.
