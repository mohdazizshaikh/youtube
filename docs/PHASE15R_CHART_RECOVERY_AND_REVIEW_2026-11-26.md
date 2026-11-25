# Phase 15R — chart-pair recovery and read-only editorial comparison

Phase 15P run 45715211323: Windows 1246 passed/67 skipped, Linux in progress at authoring. Phase 15Q run 45715678172 in progress. Phase 15R candidate, new CI pending. Last fully verified phase 15O (1298 Linux/815 hashes, 1169 Windows/63 skips).

## Chart pair backup and restore
Stop consoles. Keep original pair, original per-scene source/data/chart requests, both fonts and outer request separately. Preserve original chart_pair.json and child manifests, exact SQLite review database bytes, packet/template, media and staged assets. Backup re-audits both complete chart derivatives and rerenders charts before and after copy; metadata-only verify validates strict outer receipt, exact child snapshot inventory, video/manifest and queue state binding. Restore only to a new path; relocates only catalogs and performs full original-input re-verification. Separate snapshot pin; no encryption, live writer or power-loss guarantees.

Common original input flags: --pair PATH --pair-sha256 PIN --root PATH --request PATH --request-sha256 PIN --hindi-font PATH --hindi-font-sha256 PIN --english-font PATH --english-font-sha256 PIN.

Run python -m tools.chart_pair_snapshot backup with common flags plus --chart-pair PATH --chart-pair-sha256 PIN --snapshot NEW_PATH.
Run python -m tools.chart_pair_snapshot verify --chart-pair-sha256 PIN --snapshot PATH --snapshot-sha256 PIN.
Run python -m tools.chart_pair_snapshot restore with common flags plus --chart-pair NEW_PATH --chart-pair-sha256 PIN --snapshot PATH --snapshot-sha256 PIN.

## Chart editorial dashboard
First run bilingual_chart_pilot verify with original inputs. Stop all other review consoles. Run python -m tools.chart_review_dashboard --chart-pair PATH --chart-pair-sha256 PIN --port 8768. Open http://127.0.0.1:8768/. Read-only local comparison; fresh child technical audit at startup; receipt/scene/packet binding, pinned media and metadata check per request. Displays chart declaration and warning that transcription requires human review. No write or upload endpoints. Chart declaration hashes are not source authentication or translation proof. Original inputs are not re-rendered by the dashboard; use full verify separately. Individual queue consoles remain the write path. Close before backup or review submission.

Animated charts and transitions deferred until static chart CI is green. No new animation or chart music integration; no actual owner acceptance, publication or production merge.
