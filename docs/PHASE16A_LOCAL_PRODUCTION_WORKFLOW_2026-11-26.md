# Phase 16A — dependency-aware local production workflow foundation

Phase 15U VERIFIED_HOSTED_CI run 45717115545: Linux 1587 passed/840 hashes; Windows 1453 passed/68 skipped. Phase 15V VERIFIED_HOSTED_CI run 45717470328: Linux 1628 passed/844 hashes; Windows 1494 passed/68 skipped. W/X/Y Windows 1549/1616/1660 passed; Y 70 skips, two warnings (48 Pillow warnings removed). W/X/Y Linux pending at authoring; Z queued (45718941995). 16A new CI pending.

This narrow local slice implements the dependency/receipt principles in CORE-03; it is NOT the full canonical JobSpec state machine. Supported job kinds only: PILOT_AUDIT (fresh stopped pilot and exact inventory), PILOT_BACKUP (requires audit dependency), SNAPSHOT_AUDIT (requires backup dependency). No arbitrary commands, network, publishing, full render DAG, automatic retry, worker pool or distributed leasing. At most 32 jobs, deterministic topological order (plan order breaks ties), each step runs only one job synchronously. Separate independent chains are allowed. All prior receipts and outputs are revalidated before proceeding; source or queue change requires a new plan/workspace. Single operator, stopped inputs and private storage required.

Example plan:
```json
{"schema":"VIRALOS_LOCAL_PRODUCTION_WORKFLOW_V1","jobs":[
  {"id":"audit","kind":"PILOT_AUDIT","depends_on":[],"input":{"run":"pilot","manifest_sha256":"REPLACE_WITH_64_HEX"}},
  {"id":"backup","kind":"PILOT_BACKUP","depends_on":["audit"],"input":{"job":"audit"}},
  {"id":"verify","kind":"SNAPSHOT_AUDIT","depends_on":["backup"],"input":{"job":"backup"}}
]}
```
Run names are safe lowercase leaf directories under a private source root. Save plan and independent SHA-256 pin. Initialize exclusive new workspace:
```
python -m tools.production_workflow init --source-root PATH --workspace NEW_PATH --plan PLAN_PATH --plan-sha256 PIN
python -m tools.production_workflow step --source-root PATH --workspace PATH --plan-sha256 PIN
```
Retain each returned checkpoint_sha256 independently. Subsequent step/status commands use --checkpoint-sha256 LAST_PIN. Status is read-only but performs fresh replay of prior pilot audits and snapshot integrity checks. Step is idempotent after completion when using correct checkpoint. Each job receipt binds plan, sequence, previous receipt, prerequisite receipt pins, report and no-publication flag. Snapshots live under artifacts/JOB_ID. Exact journal/artifact inventory; stale or tampered checkpoint rejected before running verifiers. Exclusive ACTIVE_JOB.json intent persists if an error/interruption occurs; never automatically clear it or retry a potentially completed side effect. Manual inspection and new workspace required. Crash between final receipt write and intent removal also conservatively blocks. If the returned checkpoint is lost, do not trust an unpinned local receipt as independent evidence. No encryption, hostile writer, directory fsync/power loss or concurrent writer guarantee. Snapshot-only verification is not a fresh media audit. No release authority. Tests exercise graph validation, real filesystem copies (portable fixtures mock only decode), checkpoint conflicts, tampering, interruption and a separate real CPU pilot workflow.

Next: confirm outstanding 15W–Z and 16A gates, typed adapters for additional verified production stages, explicit recovery/attempt policy, resource budgets and persistent job status. Owner licensed voices, true acoustic alignment, physical Windows, historical backup and authorized account remain blocked.
