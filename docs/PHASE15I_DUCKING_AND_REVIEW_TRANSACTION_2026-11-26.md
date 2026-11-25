# Phase 15I — dynamic music ducking and recoverable independent review writes

Phase 15H verified CI run 45695488829 at dc1cac15ea2a74e27a9207e8a114989c65b2e57b: Linux 940 passed and 783 package hashes; hosted Windows 819 passed, 55 skipped. New Phase 15I candidate, CI pending.

## Review transaction
Stop all consoles and dashboards. Preserve a fresh private backup first. The prepare command accepts the existing dual-review request, freshly evaluates both reviews and creates an immutable private JSON transaction plan (no review text); retain separately trusted plan pin. The status command classifies each queue using exact manifest, original expected revision, canonical history prefix, proposed review digest, state and blocker count. The apply command requires explicit --confirm-independent-writes, revalidates both before each ordered Hindi/English write, uses existing queue.submit and rechecks both. On interruption, inspect status with the original request and plan pins. Reapplying the identical plan skips exactly recorded reviews; conflicting history, later revisions or unexpected order stop execution. No rollback or automatic replay of a changed request. This is deliberately NOT atomic across databases, not concurrent-writer safe, and not power-loss durable across filesystems. A partial write is possible; do not manually delete history. CLI commands:
```
python -m tools.bilingual_review_transaction prepare --pair /private/pair --pair-sha256 PIN --request /private/reviews.json --request-sha256 PIN --plan /private/transaction.json
python -m tools.bilingual_review_transaction status --pair /private/pair --pair-sha256 PIN --request /private/reviews.json --request-sha256 PIN --plan /private/transaction.json --plan-sha256 PLAN_PIN
python -m tools.bilingual_review_transaction apply --pair /private/pair --pair-sha256 PIN --request /private/reviews.json --request-sha256 PIN --plan /private/transaction.json --plan-sha256 PLAN_PIN --confirm-independent-writes
```
Optional --native and --native-sha256 choose native Hindi. Review preflight remains read-only. No reviewer identity or release certification.

## Dynamic ducking
Request schema VIRALOS_NARRATION_DUCK_REQUEST_V1 with mix (full Phase 15H mix request), threshold_dbfs (-50 to -20), duck_db (3 to 18), attack_ms (10–200 integer), release_ms (80–1000 integer), hold_ms (0–500 integer). Use exact-length 3–120 s mono 16k PCM16 tracks with independent pins and rights declaration. 20 ms RMS activity with one-block lookahead and hold drives sample-wise exponential music gain smoothing; base music gain is measured LUFS-derived attenuation, fades preserved. Narration remains uncompressed and timing is unchanged. Refuse source QC flags, sample overflow and output true peak beyond configured ceiling. Run:
```
python -m tools.narration_duck --voice /private/voice.wav --music /private/music.wav --request /private/duck.json --request-sha256 PIN --output /private/mix.wav
```
Output is a separate candidate; no automatic replacement of an existing reviewed pilot. RMS is not speech detection, no dynamic voice compression or limiter, no music rights certification, no human intelligibility or professional mix acceptance. Production integration and localized diagrams remain pending. No publishing or production merge.
