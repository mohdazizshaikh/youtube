# Phase 16 — unified production orchestration tracker
Date: 2026-11-26. Stable main remains Phase 13; integration PR #8 draft.

| Priority | Work | Status |
|---|---|---|
| P0 | Phase 15U/V complete hosted CI | VERIFIED_HOSTED_CI (1587/1628 Linux, 1453/1494 Windows) |
| P0 | Phase 15W–Z complete CI | VERIFIED_HOSTED_CI (W/X/Y/Z Linux 1683/1751/1796/1816, Windows 1549/1616/1660/1679) |
| P0 | 16A local typed audit/backup DAG | VERIFIED_HOSTED_CI (1869 Linux/865 hashes, 1731 Windows/72 skips) |
| P0 | Professional licensed multilingual voices and acoustic word alignment | Owner inputs / real benchmark required |
| P0 | Historical 13–20 Nov source recovery | Owner backup required |
| P0 | Gold-standard bilingual pilot and stable merge | Not accepted |
| P1 | Additional production build/verify adapters | Pending |
| P1 | Explicit failed/interrupted attempt reconciliation | 16B source candidate: pinned adoption/recheck, incomplete writes blocked |
| P1 | Typed pilot restore | 16B source candidate; fresh media audit, no overwrite |
| P1 | Resource-aware scheduler and full JobSpec state machine | 16C opt-in resource admission candidate; hard quotas, leases, parallel scheduler pending |
| P1 | Mastered video dashboard/recovery | Pending |
| P1 | Combined chart motion/transitions and audio | Pending |
| P1 | Owner Windows hardware acceptance and authorized private upload | Owner required |
| P2 | Specialist domain OS / observed analytics | Pending |
| P3 | GPU and scalable infrastructure | Pending |

16A scope: one explicit local job per step, external checkpoint pin, strict typed DAG, deterministic topological ordering, fresh prerequisite replay, exact snapshot outputs, durable intent. No publishing. No full workflow completion claim. See PHASE16A_LOCAL_PRODUCTION_WORKFLOW_2026-11-26.md.

Phase 16B source candidate, new CI pending; see PHASE16B_WORKFLOW_RECOVERY_2026-11-26.md. Full attempt/lease state machine, automatic retry, resource scheduler and generalized build/verify adapters remain pending. No owner acceptance.

Phase 16C resource policy candidate, 16B/16C full CI pending at authoring. See PHASE16C_RESOURCE_ADMISSION_2026-11-26.md. Bilingual adapters and owner acceptance still pending.
