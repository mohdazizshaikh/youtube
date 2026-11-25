# Phase 16B — typed restore and explicit interrupted-job recovery

Phase 15W/X/Y/Z verified hosted CI: Linux 1683/1751/1796/1816 passed, 848/852/856/860 package hashes; Windows 1549/1616/1660/1679 passed (68/69/70/71 skips). Phase 15Y/Z two warnings on both platforms. Phase 16A Windows 1731 passed/72 skipped/2 warnings; Linux pending at authoring (45719449499). New Phase 16B candidate, CI pending.

## Restore adapter
Existing plans remain compatible. Optional fourth job kind PILOT_RESTORE uses input {"job":"backup"} and depends_on both that PILOT_BACKUP and a SNAPSHOT_AUDIT bound to the same backup. New destination artifacts/JOB_ID; no overwrite. Calls existing non-destructive restore, checks exact snapshot payload bytes apart from relocated catalog, fresh pilot audit, queue history/revision/state, and stable restored inventory. Subsequent workflow replay audits restored output. Source/snapshot remain unchanged. Stopped private inputs, single operator.

## Recovery
An ACTIVE_JOB.json marker still blocks ordinary status/step. New tools.workflow_recovery prepare reads exact active intent and prior independently pinned receipt chain, permits at most one uncommitted receipt and one expected active artifact, rechecks every prior job, then freshly checks the active job. Read-only jobs are rechecked; completed backups can be adopted only with separately retained snapshot pin; completed restores can be adopted only against the already pinned backup and exact restored bytes plus fresh audit. Incomplete/missing write artifact stays blocked; no deleting, overwriting, replaying side effects, or clearing marker to force retry. A locally discovered snapshot hash is not independent evidence. If no trusted snapshot pin was retained, do not adopt it. Recovery plan is immutable, independently pinned, and stored outside workspace/source.

Common flags --source-root PATH --workspace PATH --plan-sha256 PIN --checkpoint-sha256 LAST_COMMITTED_PIN (omit checkpoint only for initial job).
```
python -m tools.workflow_recovery prepare [common flags] --recovery NEW_JSON
python -m tools.workflow_recovery apply [common flags] --recovery PATH --recovery-sha256 PIN --confirm-recovery
```
For interrupted backup, add --snapshot-sha256 independently retained PIN to prepare. Apply recomputes proposed receipt and checks exact plan, marker and bytes before finalizing, removes marker last, returns new checkpoint. Same pinned plan can handle interruption after receipt write but before marker removal, provided all evidence stays exact. A crash after marker removal but before receiving new pin still requires independent checkpoint recovery; never silently trust a local tip. No live/concurrent writer, hostile writer, power-loss or directory fsync guarantee. Full scheduler, attempts/leases, resource estimates, automatic retry and general production adapters pending. Tests use real filesystem and SQLite fixtures (mock decode in portable cases) and real CPU restore workflow. No publication, owner acceptance or production merge.
