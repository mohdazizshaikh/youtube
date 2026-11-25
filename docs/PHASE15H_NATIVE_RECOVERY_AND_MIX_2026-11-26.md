# Phase 15H — native recovery, coordinated preflight and audio mix

Phase 15G baseline aa92f36eacc495807b76989c9c738347b6b21372, CI 45693600947: Linux 878 passed, 777 hashes verified; Windows 759 passed, 53 skipped. Phase 15H new CI pending.

## Native pilot snapshot

Stop all editorial consoles and dashboard. A snapshot contains three independently verified child snapshots (original Hindi, English, native Hindi), pair.json, native.json and snapshot.json. Backup verifies the native derivative with its original font and request, snapshots all queues, rechecks state and source bytes. Restore creates a new root containing pair/ and native/, relocates only child catalogs, reruns native rendering/media audit and compares all queue states. Source pair and snapshots are unchanged. Use independent trusted pair, native, snapshot, font and request SHA-256 pins. Original font, native request and Phase 15C source inputs are NOT copied; retain them separately with applicable rights. The original source-bundle audit remains a separate bilingual_pilot verify. No encryption, concurrent writer protection or power-loss guarantee.

CLI:
```
python -m tools.native_pilot_snapshot backup --pair /private/pair --pair-sha256 PAIR_PIN --native /private/native --native-sha256 NATIVE_PIN --font /private/font.ttf --font-sha256 FONT_PIN --request /private/native-request.json --request-sha256 REQUEST_PIN --snapshot /private/snapshot
python -m tools.native_pilot_snapshot verify --snapshot /private/snapshot --snapshot-sha256 SNAP_PIN --pair-sha256 PAIR_PIN --native-sha256 NATIVE_PIN
python -m tools.native_pilot_snapshot restore --snapshot /private/snapshot --snapshot-sha256 SNAP_PIN --pair-sha256 PAIR_PIN --native-sha256 NATIVE_PIN --font /private/font.ttf --font-sha256 FONT_PIN --request /private/native-request.json --request-sha256 REQUEST_PIN --output /private/restored
```

## Bilingual review preflight

Request schema VIRALOS_BILINGUAL_REVIEW_PREFLIGHT_REQUEST_V1; pair_sha256, native_sha256 (null for original pair), reviews object with hindi and english, each {revision,review} using original full review envelope. Run python -m tools.bilingual_review_preflight --pair /private/pair --pair-sha256 PIN --request /private/reviews.json --request-sha256 PIN (optional --native and --native-sha256). Fresh audit, revision check, original evaluator, duplicate submission rejection and final state comparison. Returns proposed independent states, blocker counts and review pins; no reviewer text or queue writes. This is not an atomic joint submission. Submit separately via existing consoles after rechecking revisions. Owner-controlled stopped storage; do not use concurrently.

## Narration/music mix

Request schema VIRALOS_NARRATION_MIX_REQUEST_V1, voice_sha256, music_sha256, music_rights_attested=true, license_reference, music_relative_lufs (-36 to -18), fade_ms (50–1000), ceiling_dbtp (-6 to -1). Use 3–120 seconds of exact-length 16kHz mono PCM16 owner-local narration and music; no looping, trimming, resampling or music download. Run python -m tools.narration_mix --voice /private/voice.wav --music /private/music.wav --request /private/mix.json --request-sha256 PIN --output /private/mix.wav. FFmpeg measures source LUFS; music only attenuated and faded at endpoints; narration timing retained; clipping and measured output true-peak ceiling fail closed. No automatic ducking, compression, limiting, speech intelligibility or commercial-rights certification. New mix is a separate candidate, not automatically substituted into existing pilot audio; recompose and review if desired. No release or real account authorization.
