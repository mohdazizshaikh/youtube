# ViralOS — follow-on implementation evidence (24 November 2026, phase 2)

**Destination GitHub ONLY:** `mohdazizshaikh/youtube`. No reads, fetches or credentials from suspended former GitHub account. This document is a **software progress report, not owner acceptance**. Restore or publish only after separately documented owner permission and appropriate human review.

## Concrete software delivered

| Gate | New behavior and proof | Remaining restriction |
|---|---|---|
| M2.5 multilingual video | `app/localized_preview.py` + additive `sql/012_localized_preview.sql`. Fully reviewed Hindi (`hi-IN`) / English (`en-IN`, `en-US`) script variant, exact reviewer-approved shot headlines and full owner-timed caption text, actual owner-provided 16-kHz mono PCM16 WAV, FFmpeg CPU-produced **watermarked MP4**, technical QA, immutable file/input hashes and stale dependency rejection. Routes below; synthetic-tone integration test exercises a real MP4. | No automatic translation, model-generated Hindi/English voices, acoustic transcript validation, automatic duration retiming, native speaker watch-through or publishable output. Hindi preview fails closed if it detects an unverified Latin-only fallback font; genuine Devanagari glyph/ligature review is still required on target Windows. |
| M3.2 release security | PRIVATE-only upload now **requires a current M2.6 owner editorial attestation at execution**. Read-only `/readiness` response lists blockers before any network side effect. Review is tied to current final MP4, script, evidence and asset hashes; missing/stale review cannot advance intent to `IN_FLIGHT`. Mock test establishes no network call on rejected attempt; remote-unknown no-retry retained. | No live account OAuth/private upload or real authenticated Analytics executed. Owner human attestation isn't independent copyright/legal clearance. Public upload remains unavailable. |
| M4 recovery | `tools/offline_acceptance_drill.py` creates its own disposable SQLite DB/artifact; builds WAL-consistent backup, verifies checksums and migrations, restores to empty path, checks SQLite integrity. `tools/run_windows_local_acceptance.ps1` is an **owner-run** private report orchestrator for preflight, tests, CPU smoke and synthetic restore. | No physical Windows i7/32GB test has been run, no actual owner data restored. Never upload private reports, OAuth files or backups to public Git. |
| Cross-platform regression | GitHub Actions Linux CPU regression remains; Windows Server 2022 job now parses PowerShell and runs subset of portable contract tests. | Cloud Windows runner is not the owner's Windows 10/11 device. Media performance and native fonts still require real-device proof. |
| 12 domain film acceptance | `tools/domain_release_gate.py` checks locally supplied per-domain/format video + source/rights manifests using SHA-256 and reviewer-attestation fields; `docs/DOMAIN_24_VIDEO_RELEASE_MATRIX.json` starts with **0 of 24** complete. | 24 original domain-specific films, original research, licensed assets and human expert review remain unprovided. Even a completed metadata checklist is NOT legal, factual or original-content certification. |

## New API calls (opt-in, local-only)

`GET /api/m25/localized-preview/capabilities` reports technical capabilities and limitations.

`POST /api/projects/{project_id}/m25/localizations/{variant_id}/studio-preview` expects `multipart/form-data` containing `file` (owner WAV, maximum 12 MiB), `plan_json` (a strict M2 Studio plan), `owner_voice_rights_attested=true`, and `voice_origin` (nonblank provenance). The variant must already have `OWNER_REVIEWED` status and unchanged evidence dependency fingerprint. The Studio plan's locale must match that variant, each shot headline must match the reviewed on-screen text in order, and concatenated captions must exactly match the reviewed full localized script; captions are `OWNER_TIMED`, with no license-pending external footage/music. All validation and output are local; the owner narration origin and rights attestation are stored with its hash. The returned artifact is **TECHNICAL_PREVIEW_OWNER_REVIEW_REQUIRED**, never upload-ready.

`GET /api/projects/{project_id}/m25/localized-previews/{preview_id}/download` returns the watermarked MP4 only while the reviewed variant/source and file SHA remain unchanged.

`GET /api/m3/private-upload/intents/{intent_id}/readiness` is read-only and returns the precise blockers, including disabled local opt-in, stale final export, unreviewed research/rights, or absent editorial signoff. The upload execution rechecks readiness **inside** the transaction to avoid a stale preflight decision. The only network action remains explicit `UPLOAD_PRIVATE_NOW` with local opt-in, owner channel OAuth and supported reviewed final export.

## Owner Windows workflow (run locally, outside public Git)

1. With Python 3.12 and FFmpeg/FFprobe manually installed and the project extracted, choose a new **private folder** outside the source tree.
2. Run `powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\run_windows_local_acceptance.ps1 -ReportDirectory C:\Private\ViralOS-Acceptance-UniqueRun`. Script installs nothing and does not perform outbound upload or OAuth. Review each individual log; a green fixture test does not validate real owner files.
3. If desired, test `tools/offline_backup_restore.py` against a manually approved copy of real local data, with private destination, and compare a restart/cross-machine render. Never provide keyring exports or YouTube tokens in Git.
4. Register licensed local voice/CTC models and obtain owner-recorded real pronunciation samples. Native-speaker listening, word timing verification and license/provenance are mandatory.
5. After independent claim, media-rights and full final-video owner reviews, authorize only your actual owned YouTube channel and a deliberately PRIVATE supervised upload. Verify it through read-only M3.2 tools and YouTube Studio. Treat `REMOTE_UNKNOWN` as a manual reconciliation blocker, not a retry opportunity.

## 12-domain and GPU next stage

Current domain checkers validate metadata; they are not independent autonomous expert systems. Acquire rights-cleared research corpora, source-specific tools and golden fixtures for Newsroom, Science, Technology, Business, Gaming, History, Space, Learning, Sports, Career, Productivity and Culture. Produce a human-reviewed original Short + long-form for each domain (24 separate videos). Live GPU inference and multi-worker resource management remain blocked until hardware, licenses, tests and owner decision; only a dry-run routing contract exists.

## Status / no overclaims

`CODE_AND_TESTS_PASS` is distinct from `ACTUAL_LICENSED_MODEL_ACCEPTED`, `REAL_WINDOWS_HARDWARE_ACCEPTED`, `PRIVATE_YOUTUBE_ACCOUNT_ACCEPTED`, `FACTUALLY_VERIFIED`, and `PRODUCTION_RELEASED`. Lost 13–20 November remote changes cannot be invented: only an owner-held local archive can make them recoverable. No guarantees of revenue, viral performance, copyright clearance or channel monetization.
