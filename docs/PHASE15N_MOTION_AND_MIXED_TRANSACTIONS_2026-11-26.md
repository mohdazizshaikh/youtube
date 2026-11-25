# Phase 15N — step-highlight motion and mixed review transactions

Phase 15M baseline 942408d6322202929cef8c9939f89c8578e56e4a; CI run 45713389120 in progress when authored. Phase 15N candidate, new CI pending.

## Native flow motion preview
Separate artifact, NOT a regular pilot with inherited queue or review approval. Only verified native flow diagram parent; full original font/request verification through native_hindi_pilot. 25 fps, at most 60 seconds, each scene at least 15 frames. Divide each scene into three nearly equal integer stages; preserve all text, dim inactive nodes, highlight current node. Timing is equal-stage illustrative, not aligned to words. Generate bounded static stage PNGs and concatenate exact duration through FFmpeg, stream-copy parent AAC, preserve captions bytes. Audit exact stream count, format, frames, duration, decoded PCM equality with parent, and every decoded frame at 96x96 RGB against intended stage (MAE <=12 and closer to intended than other stage by >0.15). Not full resolution/pixel equality or PTS-per-frame proof. Receipt binds parent, stage images, output, captions, diagnostic. Incomplete marker until success, separate output, no queue creation. Native visual/word/rights/human acceptance pending.

Motion request fields: schema VIRALOS_NATIVE_FLOW_MOTION_REQUEST_V1, native_sha256, effect STEP_HIGHLIGHT_V1. 
```
python -m tools.native_flow_motion build --pair /private/pair --pair-sha256 PIN --font /private/font.ttf --font-sha256 PIN --visual-request /private/flow.json --visual-request-sha256 PIN --native /private/native --native-sha256 PIN --request /private/motion.json --request-sha256 PIN --output /private/motion
```
Verify same flags with verify and --motion-sha256 PIN. Keep original native and pair, font and both requests separately. No animation transitions beyond staged highlight, no motion pilot integration.

## Mixed review
First stop dashboards/consoles, run paired_production_mix verify against original inputs, take backup. Request schema VIRALOS_MIXED_REVIEW_REQUEST_V1, pair_mix_sha256 and reviews (hindi/english each {revision,review} original full review envelope). Distinct transaction schema and binding, no original-pair plan reuse. Shared preflight/history reconciliation implementation; explicit ordered independent writes, identical plan retry skips recorded submissions; no cross-DB atomicity. CLI:
```
python -m tools.mixed_review_transaction prepare --mixed /private/mixed --pair-mix-sha256 PIN --request /private/reviews.json --request-sha256 PIN --plan /private/tx.json
python -m tools.mixed_review_transaction status --mixed /private/mixed --pair-mix-sha256 PIN --request /private/reviews.json --request-sha256 PIN --plan /private/tx.json --plan-sha256 PLAN_PIN
python -m tools.mixed_review_transaction apply --mixed /private/mixed --pair-mix-sha256 PIN --request /private/reviews.json --request-sha256 PIN --plan /private/tx.json --plan-sha256 PLAN_PIN --confirm-independent-writes
```
No browser writes; run only on owner-selected stopped storage. Mixed receipt/child audit does not recompose original music; separate prerequisite. No owner review identity, publication or production merge.
