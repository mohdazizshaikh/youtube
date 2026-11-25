# Phase 15 priorities

| Priority | Gate | Status |
|---|---|---|
| P0 | Phase 14C Windows fix | VERIFIED_HOSTED_CI: run 45640671172; actual Windows owner acceptance pending |
| P0 | Offline bilingual voice QC | VERIFIED_HOSTED_CI: run 45640671172, owner voices pending |
| P0 | Phase 15B gain-only master | VERIFIED_HOSTED_CI run 45647974382; human listening pending |
| P0 | Phase 15B pronunciation coverage | VERIFIED_HOSTED_CI run 45647974382; phonetics and actual pronunciation pending |
| P0 | Phase 15B shared scene timing | VERIFIED_HOSTED_CI run 45647974382; Phase 15C hosted CI green |
| P0 | Phase 15C synchronized audio and captions | VERIFIED_HOSTED_CI run 45649764042; owner listening pending |
| P0 | Pilot render integration | VERIFIED_HOSTED_CI run 45651019863; physical owner acceptance pending |
| P0 | Native Hindi on-screen graphics | Phase 15E hosted CI green; Phase 15F VERIFIED_HOSTED_CI run 45688445729; native reader acceptance pending |
| P1 | Pair disaster recovery | VERIFIED_HOSTED_CI run 45675859895; physical owner restore pending; Phase 15H VERIFIED_HOSTED_CI run 45695488829 |
| P1 | Unified bilingual editorial dashboard | VERIFIED_HOSTED_CI run 45693600947; Phase 15H VERIFIED_HOSTED_CI run 45695488829; Phase 15I VERIFIED_HOSTED_CI run 45697364882; not atomic |
| P1 | Loudness and true peak | VERIFIED_HOSTED_CI run 45693600947; Phase 15H VERIFIED_HOSTED_CI run 45695488829; Phase 15I VERIFIED_HOSTED_CI run 45697364882; Phase 15J Linux CI failed one STATIC acoustic audit (run 45698039280); Phase 15K scene-sync ambiguity correction and paired mix candidate; owner listening pending |
| P0 | Real Hindi/English licensed TTS | BLOCKED on owner model, license, native listening and CPU measurement |
| P0 | Real CTC alignment | BLOCKED on acoustic models/reference corpus |
| P0 | Gold-standard pilot | Non-demo narration, graphics, human source/rights review and integration pending |
| P0 | Historical source | Owner offline backup required |
| P1 | Windows actual PC | Physical install, playback and disaster restore pending |
| P1 | Private YouTube | Explicit authorized real-account acceptance required |
| P1 | Automated dubbing | Translation, pronunciation, timing, video output and actual reviewer proof pending |
| P2 | 12 domain OS and GPU | Deferred until pilot acceptance |
| P2 | Analytics and monetization | Real authorized data pending; no revenue claims |

No test count is a count of production features. No production release or actual model acceptance.

Phase 15K: paired mixed-production build/verify candidate; localized diagrams, motion graphics and paired mixed-derivative recovery remain pending. Full CI must pass.
