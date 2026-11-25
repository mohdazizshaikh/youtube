# Phase 15M — native flow video and mixed editorial dashboard

Phase 15L verified CI 45706454592 at f436f74ff3ef0256a1d88ba4d7872c8f9ecd1169: Linux 1156 passed, 801 package hashes; Windows 1028 passed, 62 skipped. New Phase 15M candidate CI pending.

## Native flow MP4
Use the existing native_hindi_pilot build/verify CLI with new request schema VIRALOS_NATIVE_HINDI_FLOW_REQUEST_V1. Outer fields are pair_sha256, font_sha256, font_rights_attested=true, license_reference and scenes. Each row contains scene (1-based), title, nodes (three ordered Hindi step/label objects), source_declaration_sha256 (from the corresponding original Hindi draft manifest scene). Original full board declaration hash is recomputed; no factual or translation guarantee. Existing text-card schema remains unchanged. Flow PNGs are rendered with pinned font/RAQM and bound to the plan and receipt; original narration bytes, captions, claims/source declarations and exact timeline are preserved. New independent PENDING queue. Native receipt visual_mode DEVANAGARI_RAQM_FLOW_DIAGRAMS or legacy DEVANAGARI_RAQM_TEXT_CARDS. Both modes recognized by native snapshot and existing bilingual dashboard selectors; downstream mix selection uses same selector. No mixed visual modes within one request. Static storyboard scene PNGs, not animations; existing visual auditor samples scene midpoint.

```
python -m tools.native_hindi_pilot build --pair /private/pair --pair-sha256 PIN --font /private/font.ttf --font-sha256 FONT_PIN --request /private/flow-video.json --request-sha256 REQUEST_PIN --output /private/flow-native
python -m tools.native_hindi_pilot verify --pair /private/pair --pair-sha256 PIN --font /private/font.ttf --font-sha256 FONT_PIN --request /private/flow-video.json --request-sha256 REQUEST_PIN --output /private/flow-native --native-sha256 NATIVE_PIN
```

## Mixed editorial review
Stop existing review consoles. Use:
```
python -m tools.mixed_review_dashboard --mixed /private/mixed-pair --pair-mix-sha256 PIN --port 8767
```
Open http://127.0.0.1:8767/. Read-only comparison; fresh child media/packet audits at startup, strict paired and child receipt binding, scene mixed-audio declaration binding, pinned video and metadata revalidation per request, loopback origin/session guards and no writes. Shows original declared evidence, native visual declaration when present, mixed audio warning, independent queue status/revision and local video playback. Close before editing or backup. This dashboard does not recompose original mix inputs: separately run paired_production_mix verify with original parents, music and request before owner acceptance. Individual queue consoles remain the write path; coordinated mixed submission and browser motion director pending. Existing dashboard route behavior preserved. No network music or font retrieval. No native reader, professional listening, factual/rights, translation, real account or publication acceptance. No production merge.
