# ViralOS Launch Edition — YouTube-First Revenue Platform

**Document status:** Product/engineering specification, not working software  
**Version:** 1.1 | **Date:** 2026-11-09  
**Product owner objective:** Use ViralOS on the owner's own YouTube channels first, test its output, earn YouTube revenue, and reinvest net earnings toward an RTX A6000-class GPU. No initial client-service sales or SaaS dependence.

## 1. Mission and non-negotiables

Build a professional, local-first Windows application that transforms researched opportunities into **original, evidence-supported, engaging, upload-ready videos** and learns from real YouTube results. It must run on **Intel Core i7 8th generation, 32 GB system RAM, no dedicated GPU**, and upgrade cleanly to NVIDIA CUDA, multiple GPUs, and remote workers. Initial recurring budget target: ₹0, subject to free-source/API availability. Never guarantee virality, monetization, zero errors, or full coverage.

**Launch priorities:** (P0) reliable end-to-end creation; (P1) audience learning and growth; (P2) specialized domain depth; (P3) GPU generative studio. Do not replace the Ultimate roadmap with a small sports-only application.

## 2. Market/channel experimentation

Initial experiments: **India cricket (Hindi/Hinglish)** and **US NFL (English)** as leading candidates; **AI/technology tutorials** as a lower-footage-rights alternative. MLB, NBA, science, business, and newsroom remain in the opportunity backlog. Choose launch order from measured demand, competition, originality potential, accessible sources, production costs, and rights—not from unsupported assumptions about highest YouTube audience or RPM. Start with at most two active channels until workflow quality is demonstrated. Language per channel is configurable; no language assumption is permanent.

**Portfolio policy:** short-form for discovery and rapid testing; long-form for depth, loyalty, watch time, and potential monetization. Evergreen and timely formats should be mixed. Avoid repetitive low-value content, duplicate videos across channels, spam, or automated engagement manipulation.

## 3. MVP user journeys and acceptance tests

1. **Onboarding:** Launch Windows desktop shortcut; local web dashboard opens. Create a channel profile with niche, language, country, voice, content style, upload settings, and approval policy. **Pass:** persisted profile survives restart.
2. **Discover:** Collect available RSS/news, official sports schedules/statistics, Google Trends where accessible, YouTube public metadata within API terms, and manually supplied topics. Record source, timestamp, geography, quota, failure and freshness. **Pass:** topic cards show citations and freshness; unavailable feeds do not masquerade as coverage.
3. **Investigate:** For selected topic, create research plan, retrieve primary and independent sources, extract claims, identify contradictions, missing evidence, and source dependencies. **Pass:** each factual script claim maps to evidence or is visibly marked unsupported.
4. **Storyboard:** Generate outline, original script, hook, evidence notes, shot list, visual sources, captions, and voice instructions. **Pass:** all key claims link to source records; editorial review can edit/reject.
5. **Produce:** Create CPU-friendly visuals: custom charts, timelines, field diagrams, screen recordings, public-domain/licensed media, narration, subtitles, transitions and FFmpeg assembly. **Pass:** playable 9:16 Short and 16:9 long-form output with synchronized audio, readable captions, and render manifest.
6. **Quality gate:** Automated checks for blank frames, missing audio, subtitle overlap, duration, aspect ratio, source links, originality concerns, sensitive claims, licensed assets, and disclosure. **Pass:** blocked items cannot auto-publish.
7. **Publish:** Generate title/thumbnail/description/chapter/tag suggestions, export packages and, after OAuth authorization, optionally upload through official YouTube APIs. **Pass:** manual upload remains available; explicit approval required for sensitive material.
8. **Learn:** Import authorized YouTube Analytics where available: impressions, CTR, average view duration, retention, watch time, returning viewers, subscribers, and revenue only if accessible. **Pass:** dashboard differentiates observed values from predictions; supports per-channel experiments.
9. **Reinvest:** Track actual YouTube earnings, expenses, savings, and GPU purchase fund. **Pass:** earnings not conflated with views; purchase estimates labeled estimates.

## 4. Specialized launch-domain capabilities

### Cricket Intelligence (India)
- Official fixtures/results, teams, rosters, player performance, pitch/venue context, historical records, tactical breakdowns, controversy verification, injury source verification.
- Animated pitch and field placement diagrams, ball-by-ball *data-based* narratives where licensed data permits, original Hindi/Hinglish commentary, match previews and post-match analysis.
- Strict broadcast-footage rights checks. No presumption that adding a face, green screen, crop, speed change, or music makes reuploads monetizable or lawful.

### NFL Intelligence (US)
- Official schedules/results, play concepts, team/player statistics, injury reports, matchups, formations, contextual historical comparisons, original English tactical visualizations.
- Season-aware editorial calendar and time-zone-aware scheduling; verify claims from authoritative sports data.
- Do not republish game footage without rights or a separately assessed lawful basis; fair-use assessment is fact-specific, not an automated guarantee.

### Technology/AI Intelligence (backup/parallel pilot)
- Official documentation, version change tracking, reproducible tests, screen recordings, benchmark methodology, feature and cost comparisons, accurate tutorials.
- Prefer actual demonstrations over untested vendor claims.

### Other domain readiness
All content jobs carry `domain_id` and load category profile. Ultimate domains can be activated as plugins without altering project format.

## 5. Audience and editorial intelligence

- Topic Opportunity Score combines demand, growth, competition, audience fit, freshness, differentiation, production effort, evidence availability, and rights risk. Show components and confidence, not opaque promises.
- Audience Intent Engine identifies what viewers want: update, explanation, analysis, entertainment, or practical help.
- Narrative Director plans truthful hooks, payoff, visual pacing, and format-specific storytelling; prohibits misleading title/thumbnail claims.
- Packaging Lab stores title/thumbnail hypotheses and YouTube experiment results when permitted.
- Content Portfolio Planner balances Shorts, long-form, evergreen, series, fatigue, and cannibalization.
- Community Research captures comments/questions as leads and feedback, never proof of factual truth.
- Analytics separates correlation from causation; controlled tests when possible, not blind optimization for outrage.

## 6. Rights, integrity and policy

Every asset requires a rights record: origin URL, author/owner, license/permission, permitted uses, restrictions, attribution, expiration, evidence file. Reused footage must have meaningful original contribution **and** appropriate rights/legal assessment; these are separate questions. Record synthetic/altered-media disclosure where required. Sensitive politics, allegations, minors, personal data, and uncertain facts require human editorial approval. Corrections and takedowns must be supported. No copyright/Content ID evasion, spam, impersonation, fabricated sources, or fake engagement.

## 7. Hardware-adaptive architecture

```
Windows launcher -> React dashboard -> FastAPI API
                                       |
                                  SQLite + FTS5
                                       |
                              Job/Workflow Orchestrator
                         /             |              \
                  Domain Plugins  Evidence Store   Production Pipeline
                         \             |              /
                       Compute Provider Registry
                      /         |              \
                CPU worker   CUDA worker     Remote worker
```

**CPU baseline:** quantized small local LLM (optional Ollama/llama.cpp), sequential inference, bounded research concurrency, Piper TTS, whisper.cpp optional, FFmpeg, generated diagrams and screen capture. Use external factual sources, not model memory as verification. Resource governor monitors RAM, CPU, storage, job times and failures. Heavy text-to-video is not a baseline promise.

**Compute modes:** Auto, CPU Only, Dedicated GPU, Hybrid. Modes must be real backend configuration, not decorative UI. Capability discovery checks drivers, CUDA, free VRAM, installed model manifests, supported precision, and disk. GPU-only jobs wait with explanation if no GPU; never silently substitute poor-quality output. Job formats must be device-independent.

**Future adapters:** ComfyUI-compatible image/video workflows, GPU upscaling, model registry, shot continuity, VRAM-aware scheduler, multi-machine workers. Adapters are optional and not needed to boot MVP.

## 8. Suggested repository layout

```
viral-os/
  apps/dashboard/                 # React frontend
  apps/launcher/                  # lightweight Windows launcher
  backend/api/                    # FastAPI routes
  backend/core/                   # jobs, settings, policy, compute
  backend/domains/{cricket,nfl,technology}/
  backend/research/               # collectors, citations, claim checking
  backend/production/             # storyboard, TTS, captions, FFmpeg
  backend/publishing/             # metadata, OAuth, YouTube adapter
  backend/analytics/              # ingestion, metrics, experiments
  backend/storage/                # SQLite, migrations, file manifests
  backend/evaluation/             # quality benchmarks
  tests/{unit,integration,e2e,fixtures}/
  docs/                           # operation, licensing, model support
```

## 9. Stable data model (migration-compatible)

`channels(id, domain_id, locale, market, status, policy_id)`  
`topics(id, domain_id, observed_at, opportunity_score, confidence)`  
`sources(id, url, publisher, retrieved_at, published_at, hash, license, independence_group)`  
`claims(id, text, claim_type, confidence, verification_status)`  
`claim_evidence(claim_id, source_id, passage, timestamp, relation)`  
`research_jobs(id, domain_id, status, depth, budget, audit_log)`  
`content_projects(id, channel_id, topic_id, script_version, approval_status)`  
`shots(id, project_id, visual_spec, rights_id, asset_id, generation_mode)`  
`assets(id, origin, hash, license, attribution, expiry)`  
`renders(id, project_id, worker_id, manifest, status, output_path)`  
`publications(id, project_id, platform_id, published_at, disclosure)`  
`analytics_snapshots(id, publication_id, observed_at, metric_set)`  
`experiments(id, channel_id, hypothesis, variant, outcome)`  
`revenue_ledger(id, channel_id, period, currency, revenue, expenses, savings)`  
`workers(id, provider, capabilities, memory, availability)`

Use migration scripts, foreign keys, indices, unique idempotency keys, backups, encrypted OAuth secrets and audit events. Do not store raw secrets in SQLite plaintext.

## 10. Production pipeline

Opportunity -> source-backed research -> claim/evidence review -> original script -> shot plan -> asset/license selection -> narration -> graphics/motion -> FFmpeg render -> automated QC -> human approval -> export/upload -> analytics -> learning. Every step must be resumable and idempotent. Keep original project manifests for rerenders on future hardware.

## 11. Operational safeguards

- SQLite WAL with bounded concurrent writers, backup/restore tests, migrations, integrity checks.
- Offline mode for saved projects; explicit freshness warnings for stale sources.
- Retry with backoff, API quota counters, job cancellation/resume, render checkpoints, crash diagnostics.
- Observability: worker CPU/RAM, job duration, failure reasons, source freshness, quota consumption.
- Data privacy, channel authorization boundaries, secure token handling, safe media download processing.
- No unreviewed auto-publishing of allegations or sensitive material.

## 12. Milestones and exit criteria

**M0 — Repo audit and environment:** inspect any existing project, verify dependencies, create Windows install/launcher script and tests. Exit: clean setup on i7/32GB CPU-only machine.

**M1 — Research-to-script:** two pilot domain profiles, source registry, claim linking, original scripts. Exit: three independently reviewed example projects with traceable citations.

**M2 — CPU production:** narration, diagrams, captions, FFmpeg export. Exit: three polished Shorts and one long-form video pass technical QC and manual editorial review.

**M3 — YouTube workflow:** authorized account setup, manual export, optional API upload, channel metadata, analytics ingestion. Exit: at least one real approved upload and verified metric import (subject to account/API access).

**M4 — Learning loop:** opportunity scoring, portfolio scheduling, retention feedback, experiment tracking, corrections. Exit: repeatable weekly workflow with measured production effort.

**M5 — GPU readiness:** CPU/GPU capability registry, adapter contract, model manifest, fallback rules. Exit: mocked GPU tests and documented live-GPU validation plan.

Do not promise dates, subscribers, revenue, or monetization approval. Review official YouTube Partner Program thresholds, monetization/reused-content rules, APIs, and licensing at deployment time.

## 13. Revenue objective and dashboard

Track channel-by-channel actual revenue, eligible vs noneligible views, ad/Shorts revenue where authorized, costs, time spent, net cash flow, and savings progress. Compare multiple niches on **profit per production hour**, repeat viewers, long-form watch hours, and copyright risk—not views alone. A6000 purchase target requires a current local quote and total system-cost estimate; no invented price.

## 14. Relationship to Ultimate Edition

This is the first deployable **slice of the same platform**. Preserve IDs, schemas, job manifests, compute-provider APIs, and domain plugin contracts. Ultimate adds domain engines, evidence graph depth, cinematic generation, distributed compute and SaaS. No data migration by manual copy; use versioned migrations and compatibility tests.

## 15. Definition of done

V1 is done only when a fresh Windows install can onboard channels, research with sources, create and QC original videos, export reliably, record publication and analytics, and recover after a failed job—**without dedicated GPU**. Everything else is future work unless demonstrably tested.


---
## 16. v1.1 Gap-Closure Addendum — executable launch specification

**Document control:** This section expands v1.0; it is a specification, not implemented code. All feature claims require real tests on the target Windows i7-8th-gen/32GB/no-dGPU PC. **Scope rule:** launch focuses on the owner's YouTube channels only; no client services, sales funnel, or premature SaaS. The Ultimate blueprint remains the superset.

### 16.1 Requirement IDs and release gates

| ID | Requirement | Required evidence of completion |
|---|---|---|
| L-001 | First-run Windows installer/launcher and offline reopen | Fresh-machine setup test, restart persistence, logs |
| L-002 | Per-channel market/language/voice/brand/rights policies | Two channel profiles remain isolated across restart |
| L-003 | Sports data collection with rights and provenance | Cricket/NFL fixture, result, stats with source timestamps and stale flags |
| L-004 | Trend collector coverage and failures | Coverage dashboard displays attempted/working/failed sources, quotas |
| L-005 | Source-backed claim graph | Every factual script sentence links to supporting/contradicting evidence or review flag |
| L-006 | Domain-specific creative strategy | Cricket and NFL produce materially different format, graphics, vocabulary, and fact checks |
| L-007 | Short + long-form CPU production | Repeatable 9:16 and 16:9 renders; video/audio/caption technical QC |
| L-008 | Asset rights and reuse audit | Asset manifest blocks unknown rights and warns on broadcast footage |
| L-009 | Editorial approval and correction workflow | Cannot publish rejected content; corrections versioned |
| L-010 | YouTube OAuth and export | Authorized upload or manual package; revoked tokens fail safely |
| L-011 | Analytics and experimentation | Authorized metrics tagged with observation window; no fabricated RPM |
| L-012 | Revenue and A6000 savings ledger | Actual and projected numbers separated; expense accounting |
| L-013 | CPU/GPU/Auto/Hybrid real scheduler | CPU-only run passes; GPU jobs correctly blocked; mock CUDA adapter tests |
| L-014 | Crash recovery and backups | Interrupted render resumes or safely restarts; restore test |
| L-015 | Security and privacy | Secrets encrypted, least privilege, input sanitization, safe URLs |
| L-016 | Repeatable quality evaluation | Golden fixtures, regression suite, human review rubric |

### 16.2 First-channel experiment protocol

**Do not assume the largest audience yields the highest profit.** Run India cricket (Hindi/Hinglish) and US NFL (English) as hypotheses, with AI/Tech as a lower-rights-risk control candidate. Each pilot needs a topic backlog, audience persona, differentiation thesis, rights inventory, production budget, 4–8 week observation window (not a promise of traction), and a manual stop/continue review. Record publish cadence, content effort, impressions, CTR, 30-second retention when available, average view duration, returning viewers, subscriber conversions, copyright claims, and revenue only if eligible. Shorts and long-form are separate cohorts; never compare their raw view counts as equivalent economics. No automated spam, bulk reuploads, green-screen cosmetic transformation, or artificial engagement.

### 16.3 End-to-end operator workflow

1. Create channel profile with market, time zone, language, niche, legal/rights policy, formats, and review rules.
2. Connect permitted sources and optionally YouTube OAuth; record scopes, quotas, consent, and revocation.
3. Run trend discovery; store each observation, source URL, retrieval time, geography, duplicates, freshness, and source failures.
4. Select topic; generate explicit research questions, source plan, primary-document requirements, and a stopping rule.
5. Extract atomic claims with confidence and passage-level citations; require editorial confirmation for contested facts.
6. Choose original format: diagram-based tactical analysis, authentic tutorial, data-backed explainer, or licensed reaction with substantive commentary.
7. Generate outline, script, storyboard, asset inventory, rights manifest, voice instructions, title and thumbnail hypotheses.
8. Produce CPU-based narration, charts/diagrams, captions, scene motion, and FFmpeg exports; preserve a deterministic render manifest.
9. Run technical QA (audio peak/silence, caption bounds, blank frames, dimensions, missing assets) and factual/rights/editorial gates.
10. Human approves, edits or rejects; export/upload, then import analytics and record learnings, corrections and savings.

### 16.4 Sports-first deep requirements

**Cricket:** formats (T20/ODI/Test), innings, wickets, strike rates, economy, venue/pitch uncertainty, team/player entity disambiguation, score corrections, match state and time zone, roster/injury source quality, event significance, original pitch/field visualizations, rights-safe tactical commentary. **NFL:** season/week, offense/defense/special teams, drives, downs, yards, formations, play-clock and score context, roster/injury updates, official stats provenance, tactical route diagrams, US English editorial style, seasonality. **MLB extension:** innings, pitchers, lineups, advanced metrics with definitions, source provenance, original strike-zone/field diagrams, off-season formats. Never infer game footage rights from data availability. Do not fabricate ball-by-ball or play-by-play access where unavailable.

### 16.5 Explicit algorithm contracts

**Opportunity Score:** a transparent weighted, configurable function of observed demand, momentum, audience fit, differentiation, evidence availability, time sensitivity, estimated production effort, seasonality and rights risk. Normalize by niche and market, show missing-data penalties and uncertainty; retain each input version for later evaluation. Do not use arbitrary scores as factual virality probabilities.

**Evidence Score:** claim-level support and contradiction records; source authority for that claim, primary vs secondary status, publication time, independence group, passage match, and context. A syndication cluster counts as one provenance family. Model judgments never substitute for source text. Unsupported or disputed claims require human review or removal.

**Editorial Quality:** factual support, originality, audio intelligibility, legibility, narrative clarity, hook-to-payoff consistency, rights, disclosure and technical QA. Safety/rights are hard gates, not compensable by views.

### 16.6 Windows, performance and release engineering

Provide PowerShell setup/health-check/uninstall scripts, pinned dependency manifests, FFmpeg binary verification, optional model downloads only after consent, disk-space preflight, resource caps, local-only bind address by default, rotating logs, no hard-coded credentials, database migrations, backup/restore instructions and sample fixture media. Use one heavy CPU inference/render at a time unless measured safe. Publish an actual benchmark on the target PC: tokens/sec, 60-second video render time, RAM peak, CPU utilization, and disk consumption. Tests must not assume NVIDIA drivers exist.

### 16.7 Required artifacts and acceptance tests

Deliver actual source tree, migration scripts, documented API endpoints and schemas, UI screenshots, fixture datasets, unit/integration/e2e tests, copyright/source manifests, sample Short + long-form video, build instructions and a clean-install test report. A release cannot be marked complete from diagrams, placeholder APIs, mocked metrics, or nonfunctional UI controls.

### 16.8 Launch-to-Ultimate compatibility contract

Stable versioned `domain_id`, `channel_id`, `research_job_id`, `content_project_id`, `source_id`, `claim_id`, `asset_id`, `model_id`, `worker_id`; typed domain hooks; versioned scene/shot manifests; capability-driven worker routing; immutable source evidence; schema migrations and backward-compatibility tests. GPU generation is a new renderer adapter, not a replacement for existing project formats. Domain count and hardware are not hard-coded.
