# ViralOS Engineering Priorities — Evidence-Based Tracking

Date: 2026-11-23. Repository: `mohdazizshaikh/youtube` only.

Legend: `IMPLEMENTED_TESTED_LOCAL`, `IMPLEMENTED_NOT_LIVE_ACCEPTED`, `BLOCKED_OWNER_EVIDENCE`, `PLANNED`, `NOT_CLAIMED`.

| Gate | Work item | Actual state | Required acceptance evidence |
| --- | --- | --- | --- |
| Recovery | Historical 13–20 November unknown source commits | **BLOCKED_OWNER_EVIDENCE** | Owner-provided offline backup, hash reconciliation, actual source/test diff. Suspended GitHub account not contacted. |
| M2.4 | Hindi/English local word CTC forced-alignment algorithm/CLI | **IMPLEMENTED_TESTED_LOCAL** | Synthetic acoustic emission test + repeat token edge cases, plan/voice/locale-bound owner review. No real model loaded yet. |
| M2.4 | Professional licensed natural Hindi/English voices | **BLOCKED_OWNER_EVIDENCE** | Owner supplies suitable locally installed licensed models; audible samples, rights/consent acceptance, CPU speed and pronunciation. |
| M2.4 | Automatic translation, pronunciation dictionaries, localized on-screen graphics | **PLANNED** | Human-reviewed bilingual scripts, proper names, number retention, Devanagari typography and meaningful visuals, native watch-through. |
| M3.2 | Read-only PRIVATE video, channel and metadata verification CLI | **IMPLEMENTED_TESTED_LOCAL** | Mocked positive and failure fixtures. Does not upload a video. |
| M3.2 | Real YouTube private upload, live Analytics import, remote-unknown recovery | **BLOCKED_OWNER_EVIDENCE** | Authorized account/keyring consent, explicit independent manual private upload, API record, YouTube Studio verification, source-labeled Analytics, rollback plan. |
| M4 | Windows i7/32GB preflight | **IMPLEMENTED_NOT_LIVE_ACCEPTED** | Run `tools/windows_acceptance.ps1` on owner machine; results recorded privately. |
| M4 | SQLite database + outputs snapshot, verify, restore | **IMPLEMENTED_TESTED_LOCAL** | Tests verify immutable zip, corruption detection, clean restore and reject overwrite. Owner machine persistence drill still blocked. |
| Editorial | Source fact consistency, rights, originality and music/footage review | **PARTIAL_EXISTING_GATES** | Independent source expert, legal permissions for each asset and scored human creative review. No software proof of legal clearance. |
| 12 specialist domains | Research/creative directors | **PLANNED** | Real executable domain tools, domain-specific golden tests and original full short/long video samples; no 144-engine completion claim. |
| GPU studio | Local GPU model registry, image/video generation and benchmarking | **PLANNED** | Owner GPU + model licenses + measurable CPU fallback, non-destructive content migrations and resource tests. |
| Advanced analytics | Real cohorts, retention mapping, actual revenue and learning | **PLANNED/PARTIAL** | Real authorized data, provenance, adequate samples and experiment logs; no fabricated revenue/virality. |

**Non-negotiables:** no old suspended account interactions; no public autopublishing; no OAuth secrets in Git; no implicit Internet model fetch; owner approval of claims, rights, final video, analytics and publication.
