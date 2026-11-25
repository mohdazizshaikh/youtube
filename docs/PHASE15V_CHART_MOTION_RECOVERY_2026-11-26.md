# Phase 15V — paired chart-motion recovery

Phase 15R VERIFIED_HOSTED_CI run 45716028733: Linux 1458 passed/828 hashes; Windows 1324 passed/68 skipped. Phase 15S Windows 1369 passed/68 skipped; Linux pending. T/U CI pending at authoring. Phase 15V candidate; not a release.

## Snapshot contract
Stopped private storage only. Retain original pair, source/data/chart requests, fonts, static chart pair and motion request separately. Snapshot contains exact Hindi/English motion MP4 and caption bytes, motion_pair.json, both language packets/templates and handoff.json (10 files, plus snapshot.json). Independently retain motion, handoff and snapshot SHA-256 pins. Backup requires full motion and handoff verification before and after copying, exact inventory, internal packet/receipt consistency, bounded streaming copies and fsync. Incomplete marker remains until internal snapshot inspection succeeds. Metadata-only verify is not fresh media audit or independent parent authentication; reconstructs embedded parent declarations only for consistency. Restore to new root with motion/ and handoff/ directories, full original-input verification before removing marker. No old candidate needed. No encryption, power-loss or concurrent writer guarantees. Completed reviews/results are NOT backed up; retain separately with pins.

Common original flags: --pair PATH --pair-sha256 PIN --root PATH --chart-request PATH --chart-request-sha256 PIN --hindi-font PATH --hindi-font-sha256 PIN --english-font PATH --english-font-sha256 PIN --chart-pair PATH --chart-pair-sha256 PIN --request PATH --request-sha256 PIN.

Run python -m tools.chart_motion_snapshot backup with common flags, --motion PATH --motion-sha256 PIN --handoff PATH --handoff-sha256 PIN --snapshot NEW_PATH.
Run python -m tools.chart_motion_snapshot verify --snapshot PATH --snapshot-sha256 PIN --motion-sha256 PIN --handoff-sha256 PIN.
Run python -m tools.chart_motion_snapshot restore with common flags, --snapshot PATH --snapshot-sha256 PIN --motion-sha256 PIN --handoff-sha256 PIN --output NEW_PATH.

Unit filesystem tests mock expensive media audit but exercise actual copies and binding; existing real integration extended to verify restored media. New CI pending. Advanced transitions deferred until queued motion CI passes. No owner acceptance, publication or production merge.
