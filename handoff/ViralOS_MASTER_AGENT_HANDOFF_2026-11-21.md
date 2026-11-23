# ViralOS — MASTER PROJECT HISTORY, FEATURES & FUNCTIONS INVENTORY

**As-of:** 21 November 2026 (Asia/Kolkata).  **Purpose:** loss-resistant handoff to any AI engineering agent; record both planned and known implemented functionality.  **Project names:** ViralOS; YouTube Automation Platform; `youtube-automation-platform-cgpt` historical repository name.  **Repository restriction:** the original GitHub account has been suspended. **Do not clone, fetch, pull, push, sync, open PRs, amend remote branches or rely on the suspended remote** without a new explicit owner instruction.

> **Evidence honesty notice.** This is an exhaustive *recoverable design-and-evidence inventory* from accessible project conversation summaries and archived specification/source artifacts, not an independently verified view of the suspended repository's latest HEAD. Detailed conversations through 20 November refer repeatedly to engineering continuation, and historical summaries mention phases beyond the archived snapshot; those later implementations cannot be certified from the currently accessible code. Do not mark a feature DONE solely because it is in this document or because an earlier assistant said "continue". New agents must compare against a separately provided, lawful *local copy* or approved new repository, if one becomes available, and append—not erase—what they prove.

## 0. Status vocabulary, evidence hierarchy and non-negotiable operating rules

- **VISION**: desired future product capability, not necessarily designed at contract level.
- **SPECIFIED**: architecture/typed contract/feature behavior is written down; not executable proof.
- **IMPLEMENTED-IN-ARCHIVE**: executable implementation exists in dated source ZIP, potentially with tests; not a claim about newer remote history.
- **MOCK/LOCAL-TESTED**: development-environment test evidence, not an external end-to-end acceptance.
- **EXTERNAL-UNVERIFIED**: needs real owner credentials/accounts, an approved asset/license, hardware, network, or another external dependency.
- **ACCEPTED/RELEASED**: requires owner sign-off, reproducible build/install and retained evidence; **not established** as of the accessible evidence.

**Source priority in case of conflict:** actual audited working code + tests + real-account/hardware artifacts for implementation status; versioned canonical `v3` spec for intended behavior; ADR-001 and v2.2 video gap audit for design intent; older v1/v2 for historical lineage; chat continuation as intent/progress hints only. A schema, engine registry, profile, mock API response, example video or a green pytest run does not by itself mean production acceptance. Distinguish actual source-backed facts from a human's claim attestation.

**Safety/quality principles:** truth before virality; source traceability; independent evidence; original viewer value; copyright license gate separate from YouTube reused-content monetization; no spam, manipulated engagement, deceptive impersonation, downloaded broadcast-rights shortcut, watermark stripping, copyright evasion, fabricated subscriber/retention/RPM values, fake footage-as-news, or unsupported allegation autopublishing. High-risk material fails closed and requires human review. No guaranteed monetization, virality, 100% trend coverage, zero hallucinations or universal model support.

## 1. Product identity and business objective

ViralOS is an **owner-first, local-first Windows YouTube intelligence and audiovisual production workbench**, ultimately a hardware-scalable and optionally multi-tenant automation platform. It plans, researches, checks, scripts, visualizes, narrates, edits, exports, publishes when authorized, measures real results and learns for the next video. It is **not** merely a text-to-video wrapper or a sports-only system.

**Initial owner goal:** start with own YouTube channels, prioritize original and rights-safe India cricket in Hindi/Hinglish and US NFL in English as *test hypotheses*, optionally technology/AI tutorials (less dependent on sports footage); initially at most two active channels until quality proven. Build Shorts for discovery and longer videos for depth, watch time and loyalty. Track real costs and net revenue; save towards a future NVIDIA RTX A6000-class or other suitable GPU. Zero recurring software spend was the initial **target**, not a guarantee that every feed/API/license/model is free. No early client-services, influencer agency, client billing or SaaS-sales dependency. SaaS is deferred until owner use proves value.

**Initial computer target:** Windows 10/11 x64, Intel Core i7 8th generation, 32GB RAM, **no dedicated GPU**. No GPU must be required for the foundational source-to-original-video pipeline. FFmpeg/Python/locally approved models; GPU scale via later adapters, preserving IDs and project history. Validate measured resource use on the actual Windows machine before claiming compatibility.

## 2. Edition strategy and modular architecture

- **LAUNCH:** practical CPU research-to-video-to-review workflow for owned channels; manual/assisted publishing always available; initially sports cricket/NFL with tech optional.
- **ULTIMATE:** full federation of 12 genuine domain intelligence OSs, specialist media directors, advanced evidence verification, multilingual production, cinematic AI generation and optimization.
- **COMBINED:** single codebase with the same IDs/schema migrations; capability/edition flags reveal genuinely available functions rather than creating independent forks.
- **Planned backbone:** Windows local launcher → FastAPI service → React dashboard (target) → SQLite WAL/FTS5, migrations and filesystem blob/artifact store → durable job queue/workers → shared source/evidence/render/publish/analytics services. **Archived prototype UI is HTML/CSS/vanilla JavaScript; React is a target architecture, not a verified migrated interface.**
- **Modular monolith now**, not n8n as a required local dependency and not 144 persistent AI processes. Domain plugins hold specialist ontologies, tools, checks and creative profiles. Shared services retain network ingestion, citations, source IDs, rights, FFmpeg, TTS, fonts, OAuth and audit logic. Optional integrations may be added with versioned events later.
- **Orthogonal packs:** `DomainPolicy × FormatDirector × LocaleProfile × ChannelBrandPack × ComputeProfile`. E.g. cricket tactical Short in `hi-IN` with one channel's brand, or NFL long documentary in `en-US`, without duplicating the render engine.
- **Versioned data path:** source records → research/evidence → creative brief → narrative beats → shot/timeline/audio/overlay tracks → per-locale version → render → QC/approval → export/publish → actual metrics. Every major artifact carries ID, schema version, source/provenance/rights IDs, content hash, revision/dependency hash, review state and optional locale/brand identifiers.

## 3. Main end-to-end automated workflow

1. **Install and preflight.** Detect OS, CPU, RAM, FFmpeg, Python, fonts, free disk space, model paths and available provider capabilities; show degraded mode instead of silently failing.
2. **Create channel.** Owned channel ID/profile; niche, audience persona, country/market, primary language, optional locales, narrator/license, content style, brand kit, review and publishing policy, quota/budget.
3. **Discover topics.** Manual ideas or permitted connector observations: official feeds, RSS/Atom, Google Trends if available, YouTube public metadata and official sports info; record timestamps, coverage gaps, provider quota, market and signal trend.
4. **Score opportunity.** Explainability from growth, audience fit, novelty, demand, saturation, provenance, freshness, production cost/time, rights risk and uncertainty; not viral probability.
5. **Research plan.** Decompose questions, select sources, depth (quick/deep/forensic), budget and stop/coverage criteria, domain specialist tools.
6. **Gather evidence.** Version/hash source, capture provenance and passages; check independent corroboration, chronology, counterevidence, limits and conflicts.
7. **Fact gate.** Mark supported / disputed / unsupported / opinion / illustration / unverified; no fake sources. Serious allegations require human/legal safeguards.
8. **Original creative brief.** Define viewer question, unique thesis, expected educational/entertainment value, format, locale, channel identity, sources, asset strategy, risks and payoff.
9. **Script and narrative plan.** Hook, sections/beats, context, explanation, diagrams, payoff, honest CTA, source-to-script mapping; editable revisions.
10. **Shot and asset plan.** Classify images/screenshots/diagrams/video as evidence, original capture, licensed b-roll, illustrative simulation or reconstruction; asset-specific permission checks.
11. **Voice and language direction.** Choose licensed voice, pronunciation, text/locale, dialogue segments, real timing; plan dubbing and overlays per language.
12. **Build audiovisual timeline.** Scene/shot durations, track lanes, motion, chart/field assets, caption track, text overlays, audio mixer, transitions and safe zones.
13. **Compute admission.** CPU path by default; selected model requires compatible hardware/licensing; reserve RAM/VRAM, allow queue/checkpoint and honest fallback.
14. **Render.** FFmpeg/graphic engine into 9:16 Short, 16:9 long-form or other supported format; store intermediate hashes and output metadata.
15. **Automated QA.** Blank/silent clips, dimensions, sync, margins, captions, known source/claim mismatch, media rights, disclosures, originality, audio limits and broken links.
16. **Human review.** Watch entire actual export; check factual, legal, voice, typography and story quality; sign content/revision fingerprint. Material revisions invalidate sign-off.
17. **Output/publish.** Download a private package or MP4; owner-authenticated YouTube private upload only after specific capability and approval gates; public/scheduled auto publishing is future and policy-constrained.
18. **Observe outcomes.** Ingest actual owned-channel metrics when access exists, labeling observation/estimate/manual entry/missing value distinctly.
19. **Iterate.** Scene-level retention hypotheses, thumbnail/title/format tests, audience questions, expense/revenue analysis and reviewed content improvement proposals.
20. **Maintain and recover.** Jobs, migrations, backups, source changes, retries, corrections, revocations, model refresh and release gate validation.

## 4. Functional module catalog — user-visible capabilities and engineering behavior

### 4.1 Command Center / multi-channel manager

**Planned:** create/edit channel, show ownership/connection status, channel locale/brand/niche, content portfolio and calendar, Shorts/long mix, current jobs, sources/rights alerts, monetization eligibility *as observed*, resource capacity/quota, performance changes and GPU savings. Distinct per-channel authorization, profile, media identity, tone, review policy and archive; cross-channel near-duplicate detection. Do not claim arbitrary remote channels are connected or access exists. **Archived prototype:** working local channel/project CRUD subset and dashboard controls, not full channel-management UX.

### 4.2 Trend Observatory and source collector registry

**Planned:** RSS/news, official match schedules/stats, YouTube metadata within terms, Google Trends where accessible, Reddit, permitted social/community trends, regional/language sampling, seasonality, observation history, trend velocity/acceleration/lifecycle, creator/public competitor snapshots, alerting on score/injury/patch changes, connector health, budget/quota and coverage map. Source freshness and missing coverage are first-class visible outputs. **Archived implemented:** operator-pasted RSS/Atom XML intake and explicitly allowlisted HTTPS feed sync with permission guard/limits; manual topic/project sources, source freshness and project boundaries; no verified continuous comprehensive live discovery.

### 4.3 Opportunity and portfolio intelligence

**Planned:** explainable score from novelty, channel fit, volume/competition, timely vs evergreen potential, evidence and assets, urgency, cost, content fatigue, risk and production hours; candidate shortlist, two-channel launch limits, cross-niche experiment strategy, schedule suggestions. Separately compare profit per production hour, returning viewers and copyright risk, never invent competitor RPM. **Archive:** selected foundational rules/records, not an autonomous live market opportunity optimizer.

### 4.4 Research Studio and evidence system

**Planned:** domain research plans; source capture with IDs, dates and hashes; citations and passage offsets; source-independence graphs avoiding syndicated double-count; claim atomizer/status, conflicting sources, evidence scoring with explanation, adversarial challenger, completeness checker, alternative hypotheses, right of reply, corrections, historical memory, archived references and cross-locale update. Multimedia verification: original speech context, transcript/speaker, frame timestamp, reverse-origin clues where permitted. **Archive:** manual source/claim CRUD, project-bound links, research audit/coverage reports, review labels and human-attested statuses; not automatic independent validation of world facts.

### 4.5 Specialist domain router

**Planned:** one registry of domains, each with custom ontology, specialist calculations, validation, source preferences, editorial risks, storytelling vocabulary, motion/graphics grammars and domain-specific golden tests. Route a project, including interdisciplinary work, without 12 copies of the pipeline. **Archive:** domain IDs/profiles for all twelve, only sports Cricket/NFL prototype graphics and some bounded research path. Full specialized executable modules across twelve domains NOT verified.

### 4.6 Creator Strategy Analyzer and public competitor observation

**Planned:** learn from public channel/video titles, cadence, public view/engagement observations, hooks, chapters, transitions, topic selection and packaging, preserving observation date and sampling limitations. 120-channel benchmark research was produced historically; it is research, not an automatic intelligence feed or actual access to competitor private metrics. Do not copy a creator's scripts/visuals/brand or hallucinate private retention, advertiser income or conversion data.

### 4.7 Creative Brief, Format Director and storytelling

**Planned:** original angle/novelty thesis, intended audience, hook promise, narrative arc, problem-evidence-payoff, short/long pacing, format-specific beat policies, visual coverage by claim, ending/next-video transition, audience learning and creator brand. Formats include Shorts, long-form documentary, sports tactical analysis, live/breaking brief, technical demonstration/review, step lesson, case study, gameplay analysis, reaction/commentary; orthogonal to topic and language. **Archive:** deterministic HOOK → EXPLANATION → PAYOFF draft from owner script, editable timed shots; does not invent researched facts or claim adaptive professional creative intelligence.

### 4.8 Script Studio

**Planned:** source-linked original outlines/scripts, draft alternatives, titles/description, transitions, chapters, counterargument, quoted context, disclaimers, editable revisions, claim and source IDs and immutable final review state. **Archive:** manual scripts, revisions and bound claims; deterministic director draft; independent creative LLM and professional editing not established.

### 4.9 Storyboard, shot planner and video timeline

**Planned:** `CreativeBrief`, `NarrativePlan`, `TimedBeatGraph`, `ShotPlan`, `SceneSpec`, `VideoTimeline` with millisecond half-open intervals, scene/shot IDs, audio and overlay tracks, continuity, legal asset class, captions, camera/crop/motion, source tags, transitions, chapter structure, dynamic 9:16 / 16:9 reflow and edit-in-place revisions. Cache/reuse unaffected shots and rerender affected pieces only. **Archive:** deterministic scene plan and M2 studio compositor; full professional non-destructive editor and universal timeline not verified.

### 4.10 Seven-layer audiovisual compositor

**Planned layer grammar:** (1) canvas/background, (2) primary evidence/media/diagram, (3) secondary picture-in-picture/inset, (4) factual chart/score/arrow/source/quote overlays, (5) dialogue captions, (6) brand/disclosure/attribution, (7) player-safe zones/end-screen reserve. Timed entry/exit, fonts, contrast, hierarchy, motion constraints and factual overlays link to claim/source IDs. Avoid random stock footage, blocked content in Shorts UI zones, misleading recreation, or irrelevant motion.

**Archive:** CPU Pillow/FFmpeg-generated text/diagram overlays and moving cricket/NFL tactical markers; rights-attested PNG/JPEG stills and WAV music; no general licensed broadcast-video download/editing feature.

### 4.11 Professional audio, TTS, voice rights and sound mixer

**Planned:** narrator voice library with voice consent/license, language/accent/persona, human-supplied WAV and optional offline models, SSML/prosody control, emphasis/emotion, pronunciation dictionary for Hindi/English and names, per-sentence/scened voice generation, measured word/phoneme alignment, intelligibility, gain, fades, music ducking, ambience/SFX, sound-design profiles and loudness QC. **Archive:** owner WAV intake, per-shot conversion/normalization, segment-based timing and SRT, rights-attested background WAV mixing, optional Piper adapter and synthetic eSpeak demos. **NOT PROVEN:** professionally natural local voices, real offline Piper on owner's Windows, automatic ASR word alignment, expressive TTS at production quality. M2.4 was named the **next highest engineering priority** in the conversation: Professional Audio & Multilingual Director with tested offline voices, genuine word alignment, Hindi/English dubbing, pronunciation and localized screen graphics.

### 4.12 Multilingual and international localization

**Planned:** locale packs independent from domain/format/channel, native scripts, Devanagari + Latin font fallback, region dates/units/currency/numerals, sport terminology, glossary, Hindi/Hinglish/English and extensible languages, translated narration and titles/descriptions/thumbnails, per-locale dubbed audio, subtitles, on-screen text reflow and QA, source-claim consistency, all dependent variants invalidated on fact change. Publishing strategies: one eligible YouTube video with multiple official audio tracks if available through supported Studio workflow; or meaningfully distinct localized uploads/channels; owner review of automatic dubbing. **Archive:** owner-reviewed locale script and timed text variants, hi-IN/en-US, exported captions, owner-imported word-timing VTT, not automatic translation or full dubbing. Never assert a nonexistent YouTube audio-upload API.

### 4.13 Reactions, commentary, Shorts Remix and clip rights

**Planned:** distinguish owner-original footage, clearly licensed footage, official in-app Shorts Remix/Green Screen subject to platform capability, and unlicensed material requiring independent legal review. Intake full source/context/license, transcribe, verify, form **substantive new thesis/critique**, map permitted excerpt ranges to commentary, add original diagrams/pauses, rights/monetization checks, cite/attribute, watch full edit and monitor source restrictions/removals. No "under N seconds" copyright myth, no superficial voiceover/green screen permission assumption, no Content ID bypass/watermark removal. **Archive:** rights metadata and own stills/music; not a general third-party clip ingestion, auto-Remix or broadcast highlight downloader.

### 4.14 Sports original graphics and CPU-first render studio

**Planned:** live/source-backed scoreboard, verified stats overlay, season/tactics diagrams for each sport, arrows/player paths, time/score state, graphical recreations clearly illustrative, not fake authentic broadcast footage. CPU renders in portrait/landscape with stable overlays/voice/caption timing. **Archive:** real FFmpeg H.264 demo videos, Pillow/diagram compositor, original tactical movement Cricket/NFL, SRT/VTT export, sound input and technical checks; owner full professional acceptance still required.

### 4.15 Cinematic Prompt Intelligence Engine (CPIE) and advanced GPU generation

**Planned:** evidence-constrained shot prompt compiler; model-aware positive/negative prompts and camera/lens/composition/motion/duration/style; visual references, story/character/prop/location continuity, seed and provenance records; image-to-video/text-to-video/animation adapters, local model registry, output QA, flicker/identity drift and prompt/rights review. Model choice by license, CPU/VRAM/resolution/time/budget, cache and fallback. Future multi-GPU/remote workers. **Archive:** typed specs only for most generative features, not validated RTX 3090/A6000 or photorealistic generation.

### 4.16 Image assets, typography and thumbnails

**Planned:** source-led visual selection, original charts/infographics, licensed/archive assets and attribution, language-aware title cards, safe mobile typography, contrast/color/accessibility, copyright-safe images, thumbnail originality and audience testing. Thumbnail/title hypotheses tracked against observed owned-channel data. **Archive:** diagrams, stills and timed text overlays; not a proven intelligent thumbnail design/CTR experiment system.

### 4.17 Quality assurance and editorial council

**Planned:** machine technical checks: black frames, audio dropout, dimensions, caption timing, readable overlays, aspect ratio, unsafe z-order, duplicated frames, asset provenance, license expiration, claim-source/shot link, accurate score/date/units, synthetic disclosure, anti-repetition, originality. Domain-specific critics (scientific equations, NFL terms, newsroom quote context, etc.) and human full-watch review. A final file hash binds review; changes revoke approvals. **Archive:** QC manifests, creative audit, rights/source review and final-owner approval fingerprint; only bounded technical checks, not automatic professional film evaluation, legal determination or full factual certification.

### 4.18 Publisher and YouTube account integration

**Planned:** official owned-channel OAuth, exact channel-ID cross-check, least-privilege scopes, keyring tokens, owned-channel policy/quotas, original metadata, truthful thumbnails/titles, playlists, private draft/upload, status reconciliation, scheduling only after approval, separate safeguards for public release, corrections/takedown/rollback. Distinguish pre-publish preview, local final export and real YouTube visibility state. **Archive:** 12-Nov M3 optional private-upload intent/execute adapter with `VIRALOS_ENABLE_PRIVATE_UPLOAD` default OFF, Google desktop OAuth helper and mocked paths. Earlier generic `/api/youtube/upload` intentionally rejects 403. No credentialed external private upload proven; no public unattended upload certified.

### 4.19 Audience Analytics and retention/learning lab

**Planned:** only authorized owner channel Analytics API; impressions, views, CTR when available, watch time, average view duration, retention graph, return viewers, subscribers, source, audience region/language, Shorts vs long comparisons and sample-size caveats. Map retention events to scenes/creative hypotheses, compare matched cohorts, separate correlation from causality. Community question/reaction/correction mining where permitted. **Archive:** owner-entered labelled observations, optional read-only Google YouTube Analytics helper with OS keyring, date-range sync and channel-ID verification in code; live result unverified; no automatic sophisticated retention learning established.

### 4.20 Earnings, costs, monetization and GPU fund

**Planned:** actual YouTube revenue only when authorized/exposed; separately track Shorts/long ads where available, other actual owner-entered earnings, expenses, production labor/hours, profitability, risk, eligible vs unmonetized views, tax/fee assumptions (if supplied), savings against owner-entered GPU purchase price, target progress and monthly cash flow. Report estimated/observed/missing sources distinctly. Monitor YPP eligibility and policy updates but never guarantee approval or revenue. **Archive:** some ledger/contracts/owner-observed analytics support; independent channel revenue import and reliable real GPU-fund dashboard not verified.

### 4.21 Job scheduler, retries and operational resilience

**Planned:** durable DAG tasks with QUEUED/RUNNING/RETRY_WAIT/BLOCKED/WAITING_FOR_APPROVAL/WAITING_FOR_CAPABILITY/SUCCEEDED/FAILED/CANCELLED; idempotency keys, resource budgets, bounded retries, checkpoints, cancellation/resume, crash recovery, rate limits/quota accounting, artifact manifests, source freshness alerts, duplicate remote-upload reconciliation (`REMOTE_UNKNOWN` must not auto-retry). **Archive:** local preview queues/retry paths and DB migrations, private-upload uncertainty safeguards; full crash/drill durability and distributed queue not accepted.

### 4.22 Install, offline, model management, security and data portability

**Planned:** Windows first-run guided launcher, local-only dashboard bind `127.0.0.1`, Python/FFmpeg preflight, system fonts, localhost API docs, offline reopening of saved projects, source freshness warnings, approved model download/install with license, CPU/GPU/memory/power/disk telemetry, safe download parser/network controls, keyring OAuth, token redaction, backed-up SQLite/data outputs and restore drill, migration/rollback test, versioned ZIP exports and portability, future PostgreSQL/SaaS identity/RBAC/tenant isolation. **Archive:** PowerShell startup scripts, Python/FastAPI local host, 8 SQL migrations, source limits/permissions, OS-keyring code, package checks; actual owner's Windows performance/security acceptance not proven.

### 4.23 Open API, typed contracts and agent handoff

**Planned:** stable OpenAPI routes with request/result schemas, source/evidence/project IDs, domain/format/locale/brand manifest, operational exceptions and test traceability. Human-reviewed corrections and version changes propagate through dependencies. All toggles must map to backend operation or be visibly disabled. Maintain machine-readable requirements registry, decision log, ADRs, release notes, milestones, blockers, evidence and verification paths; prevent feature-completion inflation. **Archive:** source contains real routes, tests, SQL, specs and manifests. This inventory adds a loss-resistant snapshot but **does not replace lost commits**.

## 5. The twelve distinct Domain OSs — exact scope

Each Domain OS has expert **Discover → Investigate → Verify → Reason → Create → Publish → Learn** logic and **its own visual storytelling grammar**. These are not separate websites or guaranteed implemented executables; the archived Combined v3 engine registry declares 144 engine *specifications* in total.

1. **Newsroom / Investigative OS:** high-fidelity full speech and event context; speaker/quote chronology and historical statement memory; consistency/position-change/contradiction classifications; promise vs policy vs executed action vs outcome; budgets, bills, orders, filings, procurement, right-of-reply and evidence-weighted different perspectives; media ownership and public influence network with alternative explanations; forensic investigation and corrections; timestamped document quote cards, archive timeline and labeled reconstruction; strong privacy/legal risk gates.
2. **Science OS:** paper/preprint discovery; authors/journals/status, peer review, study design, sample and effect sizes, statistics, replication, uncertainty, consensus and retractions; scientific calculator, mechanism explainer, genuine vs illustrative charts and simulator labels; domain scientific challenger, limitations and source fidelity.
3. **Technology OS:** release/docs/patch tracker, vendor assertion versus reproducible hands-on evidence, hardware/software version/license/budget matrix, benchmark normalization, security/privacy checks and bug reproduction; source-code/screen capture walkthroughs, demo/review/tutorial creative grammar, observed conditions and version-drift alerts.
4. **Business OS:** annual/quarterly filings, income/balance/cash flow and arithmetic reconciliation, currency/period assumptions, ownership/funding and influence, competitor market structure, unit economics, valuation/forecast sensitivities and governance conflicts; sourced charts with audited/estimated labels; not unqualified investing advice.
5. **Gaming OS:** original gameplay capture, publisher permission, patch/meta/mechanics monitoring, replay analytics, genuine highlight selection, strategy explanations, spoiler policy, community Q&A, HUD-safe visual storytelling and attribution; never imply all third-party gameplay is automatically reusable.
6. **History OS:** archival source explorer, provenance/authenticity checks, primary documents, period chronology/geography, conflicting historians, myth challenge, translation review and uncertainty; artifact reveals, maps and reconstruction director with artistic-simulation labels.
7. **Space OS:** missions/observations, papers and instrument context, orbital/unit computations, mission history, cosmic scale comparison, imaging provenance, gravity/physics critic and myth checks; truthful animations distinguish observations from artistic visualizations.
8. **Learning / Education OS:** explicit learning outcomes, prerequisites, misconceptions, graduated worked examples, lesson plans and exercises, assessment design, accessibility and feedback; whiteboard/reveal diagrams, stepwise teaching with comprehension checkpoints.
9. **Sports OS:** shared sport entity resolver, fixtures, scores, timelines, performance stats, injury/roster, seasonality, tactics board, fan questions and preview/review; original field diagrams and strict rights checks. Subadapters: **Cricket** overs/balls/wickets/innings/powerplay/batting-bowling and pitch tactics; **NFL** downs/distance/clock/drives/formation/coverage and gridiron animation; **MLB** innings, pitcher-hitter, strike zone/offseason; **NBA** possessions and court tactics; **Soccer** xG provenance, formations and match events. None should invent official match data or assume league broadcast rights.
10. **Career OS:** region-level labor demand and dated job data, salary distribution with caveats, skill/credential maps, career transitions, interview/resume projects, portfolio, job-market risk and no inflated income/placement promises.
11. **Productivity OS:** source-safe workflow recorder, bottleneck analysis, automation recipe, permission and rollback checks, observed before/after time use, templates, tool comparison, tested demonstrations and no fictional efficiency multiplier.
12. **Culture / Internet OS:** origin and diffusion of memes/trends, earliest observable posts, cultural context, rumor/deepfake challenge, source attribution, identity/minor/harassment safeguards, network/timeline visuals and original commentary rather than pile-ons.

Other future specialist profiles (finance, politics, health, entertainment, education submarkets and regional languages) require additional policies and are *not* counted as completed top-level OSs.

## 6. Format, brand and locale system

| Dimension | Planned types | Required invariant |
|---|---|---|
| Format | Short explainer; long documentary; tactical analysis; breaking brief; demo/review; step lesson; reaction review; case study; gameplay analysis; sports preview/postgame, evergreen, tutorial | Same topic may produce meaningfully different original formats, not copy-pasted low-value mass videos |
| Aspect/output | 9:16, 16:9; other approved frame/caption layouts | Captions, faces, fields, scoreboxes and disclosures fit each target player |
| Locale | Initially hi-IN/Hinglish and en-US; extensible | Translation applies to speech **and** overlays, typography, dates, units, numerals, CTA/metadata |
| Brand | Voice license, color, intro/outro, logo, persona, pace, title/thumbnail style, upload policy | Per-channel identity and rights stay separate even in same domain |
| Compute | CPU, compatible NVIDIA CUDA, hybrid, remote later | Same source IDs and content projects; clear capability gate and resource fallback |
| Publishing | local preview, private review ZIP, approved final MP4, opt-in private owner upload, other modes only after acceptance | No automatic public publishing or made-up feature availability |

## 7. Verification history and dated development lineage

**8–9 Nov 2026:** Launch, Ultimate and AgentReady v2 documentation; 12 OS schema/144 engine declarations; v2.1 structural pack validator; independent reality audit showed the early ZIPs were **mostly design**, not 144 runnable engines, and listed 25 missing audiovisual contracts. Competitor study and 120-channel public benchmarking were researched. ADR-001 proposed one shared CPU-first modular monolith and domain×format×locale×brand creative architecture. Separate v3 spec packs then included more typed creative contracts and registry coverage. **These artifacts are requirements, not acceptance evidence.**

**11 Nov 2026:** M0 local workbench and M2 Studio intermediate source ZIPs/demo media are preserved in the Library. They show actual code for local UI, backend and technical CPU preview; owner Windows/live-account proof absent.

**12 Nov 2026:** The preserved `ViralOS_Launch_M2_2_M3_v0_5_Working_Source.zip` has Python FastAPI backend, local HTML/CSS/JS frontend, eight SQL migrations (001–008), tests, FFmpeg/Pillow audio-video render and private-review/owner-final-export path. `ViralOS_M2_2_M3_BUILD_REPORT.json` records **51 automated tests** run in Linux with FFmpeg and synthetic eSpeak, and explicit **false** values for real YouTube OAuth/upload/analytics, target Windows hardware, natural-quality voice and GPU live tests. Optional private-upload adapter is opt-in and code/mocks tested, not confirmed remotely.

**15–20 Nov 2026:** Project history shows repeated "continue" engineering-update turns, including next-gate requests; one explicit strategic direction names **M2.4 Professional Audio & Multilingual Director** as highest priority and **M3.2 Real-Account Acceptance** (supervised owned-channel private upload, real authorized analytics/revenue, rollback/recovery) afterward. The user previously asked for git synchronization and tracking documents. **No dated 15–20 Nov repository code, test logs, exact feature diffs or external acceptance artifacts are accessible in this reconstruction.** Some later conversations may refer to phases 76–80, but their executable state must remain `UNVERIFIED_LATER_HISTORY` until independent local evidence exists. Do not overwrite the known 12-Nov baseline with guessed phase completion.

**21 Nov 2026:** Suspended original GitHub account reported; owner expressly forbids any pull/push. This inventory is constructed from chat context and available pre-existing Library artifacts. No network Git operations performed.

## 8. Priority engineering gates and definition of done

**Immediate recovery gate:** locate *only* owner-approved offline copy/backups later; checksum and inventory without contacting suspended GitHub; compare current code to this handoff, make new local baseline, reconstruct commit/phase matrix. Avoid loss from assuming the old account can be restored. Nothing in this document authorizes any Git operation.

**M2.4 — Professional Audio & Multilingual Director:** real locally licensed Hindi/English voices benchmarked on target Windows CPU; pronunciation names/sports terms and expressive prosody; proper measured word alignment not merely scene estimates or imported timestamps; scene dubbing, overlay title/label translation, reflow, sound mixing, audio rights and complete QC. Golden English and Hindi sample checked by human listeners. Missing models or expensive compute must fail visibly.

**M3.2 — Real-Account Acceptance:** owner consent to own Google/YouTube channel OAuth; exact channel identity and secure keyring; bounded supervised PRIVATE upload of reviewed rights-safe final MP4; inspect YouTube Studio private status and metadata; simulate uncertain network result, avoid duplicate upload and verify correction/revocation/retry; obtain authentic Analytics observations; actual authorized revenue source if available or label missing; owner signs acceptance. These are **gates, not achieved facts**.

**M4 — Production durability/learning:** real topic-source pilot, human quality reviews, retention experiments grounded in actual data, SQL backup/restore drills, crash recovery, source freshness correction cascade, quotas, security and resource regressions.

**Domain expansion gate:** each of 12 specializations needs not just profile documents but at least one complete 9:16 and one 16:9 representative sample with actual specialty algorithms, independent data/rights sourcing, domain-specific golden fixtures, human review and limitations.

**GPU readiness gate:** capability manifests, adapter contracts, model licensing/digests, CPU fallback/no-hardware test, optional CUDA/3090/A6000 benchmarks and multi-worker security/portability. Avoid choosing a GPU model or promising speed/quality without measurements and an owner quote.

**Release gate:** fresh Windows setup and restart persists data; genuine evidence-backed video + human fully watches; audio/graphic/captions/rights pass; optional authorized private publishing and real analytics verified if advertised; crash/restart/backup/restore tested; versioned installer and rollback documented. The phrase DONE means **specified → implemented → tested → owner accepted → released**, not just generated code, green docs or plausible mock.

## 9. Known blockers, unresolved dependencies and honest non-features

- Missing visibility into suspended repository HEAD, exact later phases/commits, owner local branch/backups and newer test reports.
- Windows i7/32GB no-GPU setup/timing/font playback not independently observed at archive date.
- No supplied OAuth client consent, owned YouTube IDs/Studio sessions, live analytics or real public/private upload evidence in archived reports.
- No verified real external sports-data licenses, broadcast/Remix rights or source archive completeness.
- No guaranteed natural Piper voice model, true forced per-word alignment, auto-dubbed Hindi/English final video, or production-quality music rights.
- No demonstrated universal 12-domain OS implementation, source independence challenger, autonomous LLM truth verification, fully automated professional video editor or compliant clip remix pipeline.
- No validated NVIDIA CUDA model inference, GPU/video generation, remote workers, distributed queue or SaaS security tenant isolation.
- No validated monetization/YPP decision, real earnings import or predicted profits; channel strategy remains empirical.
- No supported claim that 144 registered engines are 144 tested AI services; registry **SPECIFIED** status is not execution status.
- No unreviewed allegations, illicit downloads, fake engagement, auto-public uploads or guaranteed zero-error viral growth should ever be added.

## 10. Copy-ready AI-agent execution contract

**Agent role:** maintain and extend one original, rights-safe, source-traceable, local-first ViralOS platform for owner-owned channels. Follow current owner instruction: **do not pull, push, clone or otherwise touch suspended GitHub remote**. Respect this handoff as *reconstructed requirements/status evidence*, not as a proof the latest code exists.

1. Inventory any future **owner-provided local** source tree read-only; record paths, hashes, branch/commit info if locally available, build/date, test manifest, untracked work and missing artifacts. Never invent provenance or treat a ZIP packaging timestamp as deployment acceptance.
2. Create `FEATURE_MATRIX` with IDs, planned/implemented/tested/accepted/released states, dependencies, owning module, precise tests and owner-blocked items. Separate every design contract and sample from running integration.
3. Keep one canonical database lineage and all existing migrations; preserve project/source/claim/render/channel identities. No schema rewrite without backwards-compatibility migration tests.
4. Work in small bounded engineering gates; each increment includes code, negative/fail-closed tests, documentation, sample output and reproducible command logs. Never claim real OAuth, money or live feed success without owner-authorized evidence.
5. Prioritize M2.4 professional local voice/alignment/localization, then M3.2 supervised private owned-channel acceptance, then durability/learning/domain depth/GPU; do not convert prototype to an autopublisher by bypassing review.
6. Keep known policies: claims need evidence, not LLM memory; owner review and rights are separate from YouTube monetization; synthetic reconstructions labelled; translations revalidated; stale approval invalidated; private upload exact channel verified; network `REMOTE_UNKNOWN` outcome blocks blind reupload.
7. Produce a concise handoff each milestone: changed files/modules, schema migration, tests count/results/environment, UI/API evidence, real video hashes, blockers, next gate. If test execution is unavailable, say **NOT RUN** and why.
8. Do not replatform prematurely, split 12 renderer copies or introduce n8n/SaaS/cloud/GPU as a compulsory Launch dependency.

**The project is successful only when users can reliably create original, compelling, researched audiovisual videos under real review, with clear boundaries on rights and truth, accurate owned-account measurements, resilient local operations and a measurable path to scaling.**

## Appendix A — Exact 144-engine specification registry (not 144 implemented engines)


### SHARED — 26 engine declarations

| Engine ID | Planned purpose | Historical registry status |
|---|---|---|
| `shared.connector_registry` | source connectors and permitted provider quotas | SPECIFIED / **executable not verified** |
| `shared.trend_observatory` | topic time series, source coverage and lifecycle | SPECIFIED / **executable not verified** |
| `shared.opportunity_score` | source-backed explainable recommendation score | SPECIFIED / **executable not verified** |
| `shared.research_planner` | research questions, stopping criteria and budget | SPECIFIED / **executable not verified** |
| `shared.source_version_store` | immutable evidence captures and hashes | SPECIFIED / **executable not verified** |
| `shared.evidence_graph` | atomic claims and source passage edges | SPECIFIED / **executable not verified** |
| `shared.source_independence` | syndication groups and provenance relations | SPECIFIED / **executable not verified** |
| `shared.adversarial_challenger` | strongest opposing evidence and open questions | SPECIFIED / **executable not verified** |
| `shared.research_completeness` | unanswered question and coverage auditor | SPECIFIED / **executable not verified** |
| `shared.domain_router` | domain plugin selection, relevance and different angles | SPECIFIED / **executable not verified** |
| `shared.editorial_decision_council` | risk policy, resource allocation and human gate | SPECIFIED / **executable not verified** |
| `shared.narrative_director` | honest hooks, intent and original source-backed story | SPECIFIED / **executable not verified** |
| `shared.portfolio_optimizer` | content balance, fatigue and duplicate prevention | SPECIFIED / **executable not verified** |
| `shared.creator_strategy_analyzer` | public technique analysis without copying | SPECIFIED / **executable not verified** |
| `shared.script_to_scene_planner` | structured SceneSpecs sourced to script and claims | SPECIFIED / **executable not verified** |
| `shared.rights_and_originality` | license, original value and reused media gates | SPECIFIED / **executable not verified** |
| `shared.cpu_media_renderer` | diagrams, TTS, subtitles, FFmpeg CPU outputs | SPECIFIED / **executable not verified** |
| `shared.cinematic_prompt_compiler` | model-specific shot prompt with model evidence | SPECIFIED / **executable not verified** |
| `shared.motion_continuity` | character, prop, location and motion reference control | SPECIFIED / **executable not verified** |
| `shared.temporal_visual_qa` | flicker, identity drift, scientific and factual scene checks | SPECIFIED / **executable not verified** |
| `shared.compute_scheduler` | CPU/CUDA/hybrid/remote admission and reservations | SPECIFIED / **executable not verified** |
| `shared.model_registry` | model digest, license, hardware and capabilities | SPECIFIED / **executable not verified** |
| `shared.publishing_director` | metadata, approval and official authorized publishing | SPECIFIED / **executable not verified** |
| `shared.analytics_learning` | authentic analytics, experiments and corrections | SPECIFIED / **executable not verified** |
| `shared.revenue_gpu_fund` | actual earnings minus costs and savings towards GPU | SPECIFIED / **executable not verified** |
| `shared.job_recovery` | state transitions, retries, checkpoint, backup and diagnostics | SPECIFIED / **executable not verified** |

### NEWSROOM — 12 engine declarations

| Engine ID | Planned purpose | Historical registry status |
|---|---|---|
| `newsroom.event_verification` | event verification | SPECIFIED / **executable not verified** |
| `newsroom.full_speech_parser` | full speech parser | SPECIFIED / **executable not verified** |
| `newsroom.claim_atomizer` | claim atomizer | SPECIFIED / **executable not verified** |
| `newsroom.historical_statement_memory` | historical statement memory | SPECIFIED / **executable not verified** |
| `newsroom.consistency_contradiction` | consistency contradiction | SPECIFIED / **executable not verified** |
| `newsroom.policy_action_outcome` | policy action outcome | SPECIFIED / **executable not verified** |
| `newsroom.perspective_counterevidence` | perspective counterevidence | SPECIFIED / **executable not verified** |
| `newsroom.media_ownership_influence_graph` | media ownership influence graph | SPECIFIED / **executable not verified** |
| `newsroom.right_of_reply` | right of reply | SPECIFIED / **executable not verified** |
| `newsroom.investigative_memory` | investigative memory | SPECIFIED / **executable not verified** |
| `newsroom.newsroom_visual_policy` | newsroom visual policy | SPECIFIED / **executable not verified** |
| `newsroom.newsroom_legal_review` | newsroom legal review | SPECIFIED / **executable not verified** |

### SCIENCE — 8 engine declarations

| Engine ID | Planned purpose | Historical registry status |
|---|---|---|
| `science.paper_discovery` | paper discovery | SPECIFIED / **executable not verified** |
| `science.methods_examiner` | methods examiner | SPECIFIED / **executable not verified** |
| `science.quantitative_calculator` | quantitative calculator | SPECIFIED / **executable not verified** |
| `science.replication_consensus` | replication consensus | SPECIFIED / **executable not verified** |
| `science.mechanism_explainer` | mechanism explainer | SPECIFIED / **executable not verified** |
| `science.retraction_monitor` | retraction monitor | SPECIFIED / **executable not verified** |
| `science.scientific_visualizer` | scientific visualizer | SPECIFIED / **executable not verified** |
| `science.adversarial_scientific_review` | adversarial scientific review | SPECIFIED / **executable not verified** |

### TECHNOLOGY — 8 engine declarations

| Engine ID | Planned purpose | Historical registry status |
|---|---|---|
| `technology.release_monitor` | release monitor | SPECIFIED / **executable not verified** |
| `technology.vendor_claims_extractor` | vendor claims extractor | SPECIFIED / **executable not verified** |
| `technology.reproducible_test_harness` | reproducible test harness | SPECIFIED / **executable not verified** |
| `technology.benchmark_normalizer` | benchmark normalizer | SPECIFIED / **executable not verified** |
| `technology.security_privacy_examiner` | security privacy examiner | SPECIFIED / **executable not verified** |
| `technology.cost_license_analyzer` | cost license analyzer | SPECIFIED / **executable not verified** |
| `technology.tutorial_compiler` | tutorial compiler | SPECIFIED / **executable not verified** |
| `technology.version_drift_monitor` | version drift monitor | SPECIFIED / **executable not verified** |

### BUSINESS — 8 engine declarations

| Engine ID | Planned purpose | Historical registry status |
|---|---|---|
| `business.filing_intake` | filing intake | SPECIFIED / **executable not verified** |
| `business.financial_normalizer` | financial normalizer | SPECIFIED / **executable not verified** |
| `business.arithmetic_auditor` | arithmetic auditor | SPECIFIED / **executable not verified** |
| `business.ownership_influence` | ownership influence | SPECIFIED / **executable not verified** |
| `business.unit_economics` | unit economics | SPECIFIED / **executable not verified** |
| `business.competitive_landscape` | competitive landscape | SPECIFIED / **executable not verified** |
| `business.forecast_sensitivity` | forecast sensitivity | SPECIFIED / **executable not verified** |
| `business.governance_adversarial_review` | governance adversarial review | SPECIFIED / **executable not verified** |

### GAMING — 8 engine declarations

| Engine ID | Planned purpose | Historical registry status |
|---|---|---|
| `gaming.game_patch_monitor` | game patch monitor | SPECIFIED / **executable not verified** |
| `gaming.mechanics_knowledge` | mechanics knowledge | SPECIFIED / **executable not verified** |
| `gaming.replay_ingest` | replay ingest | SPECIFIED / **executable not verified** |
| `gaming.highlight_selector` | highlight selector | SPECIFIED / **executable not verified** |
| `gaming.strategy_evaluator` | strategy evaluator | SPECIFIED / **executable not verified** |
| `gaming.community_question_miner` | community question miner | SPECIFIED / **executable not verified** |
| `gaming.gameplay_storyteller` | gameplay storyteller | SPECIFIED / **executable not verified** |
| `gaming.publisher_rights_checker` | publisher rights checker | SPECIFIED / **executable not verified** |

### HISTORY — 8 engine declarations

| Engine ID | Planned purpose | Historical registry status |
|---|---|---|
| `history.archive_explorer` | archive explorer | SPECIFIED / **executable not verified** |
| `history.provenance_authenticity` | provenance authenticity | SPECIFIED / **executable not verified** |
| `history.chronology_builder` | chronology builder | SPECIFIED / **executable not verified** |
| `history.historical_geography` | historical geography | SPECIFIED / **executable not verified** |
| `history.historiography_challenger` | historiography challenger | SPECIFIED / **executable not verified** |
| `history.myth_checker` | myth checker | SPECIFIED / **executable not verified** |
| `history.translation_reviewer` | translation reviewer | SPECIFIED / **executable not verified** |
| `history.reconstruction_director` | reconstruction director | SPECIFIED / **executable not verified** |

### SPACE — 8 engine declarations

| Engine ID | Planned purpose | Historical registry status |
|---|---|---|
| `space.mission_monitor` | mission monitor | SPECIFIED / **executable not verified** |
| `space.observation_paper_research` | observation paper research | SPECIFIED / **executable not verified** |
| `space.orbital_unit_validator` | orbital unit validator | SPECIFIED / **executable not verified** |
| `space.cosmic_scale_graphics` | cosmic scale graphics | SPECIFIED / **executable not verified** |
| `space.imaging_provenance` | imaging provenance | SPECIFIED / **executable not verified** |
| `space.space_myth_checker` | space myth checker | SPECIFIED / **executable not verified** |
| `space.mission_timeline_director` | mission timeline director | SPECIFIED / **executable not verified** |
| `space.physics_critic` | physics critic | SPECIFIED / **executable not verified** |

### LEARNING — 9 engine declarations

| Engine ID | Planned purpose | Historical registry status |
|---|---|---|
| `learning.objective_decomposer` | objective decomposer | SPECIFIED / **executable not verified** |
| `learning.prerequisite_mapper` | prerequisite mapper | SPECIFIED / **executable not verified** |
| `learning.misconception_finder` | misconception finder | SPECIFIED / **executable not verified** |
| `learning.lesson_planner` | lesson planner | SPECIFIED / **executable not verified** |
| `learning.example_generator` | example generator | SPECIFIED / **executable not verified** |
| `learning.assessment_builder` | assessment builder | SPECIFIED / **executable not verified** |
| `learning.explanation_critic` | explanation critic | SPECIFIED / **executable not verified** |
| `learning.accessibility_layout_director` | accessibility layout director | SPECIFIED / **executable not verified** |
| `learning.learning_outcome_reviewer` | learning outcome reviewer | SPECIFIED / **executable not verified** |

### SPORTS — 28 engine declarations

| Engine ID | Planned purpose | Historical registry status |
|---|---|---|
| `sports.event_calendar` | event calendar | SPECIFIED / **executable not verified** |
| `sports.entity_resolver` | entity resolver | SPECIFIED / **executable not verified** |
| `sports.stat_validator` | stat validator | SPECIFIED / **executable not verified** |
| `sports.performance_trend` | performance trend | SPECIFIED / **executable not verified** |
| `sports.tactics_board` | tactics board | SPECIFIED / **executable not verified** |
| `sports.injury_roster_monitor` | injury roster monitor | SPECIFIED / **executable not verified** |
| `sports.match_storyline` | match storyline | SPECIFIED / **executable not verified** |
| `sports.rights_safe_footage_planner` | rights safe footage planner | SPECIFIED / **executable not verified** |
| `sports.sports_community_questions` | sports community questions | SPECIFIED / **executable not verified** |
| `sports.seasonality_planner` | seasonality planner | SPECIFIED / **executable not verified** |
| `sports.cricket_fixture_score_intake` | cricket fixture score intake | SPECIFIED / **executable not verified** |
| `sports.cricket_score_semantics` | cricket score semantics | SPECIFIED / **executable not verified** |
| `sports.cricket_tactical_graphics` | cricket tactical graphics | SPECIFIED / **executable not verified** |
| `sports.cricket_editorial_angles` | cricket editorial angles | SPECIFIED / **executable not verified** |
| `sports.cricket_rights` | cricket rights | SPECIFIED / **executable not verified** |
| `sports.nfl_schedule_status` | nfl schedule status | SPECIFIED / **executable not verified** |
| `sports.nfl_play_state_parser` | nfl play state parser | SPECIFIED / **executable not verified** |
| `sports.nfl_tactics_animator` | nfl tactics animator | SPECIFIED / **executable not verified** |
| `sports.nfl_performance_analysis` | nfl performance analysis | SPECIFIED / **executable not verified** |
| `sports.nfl_rights` | nfl rights | SPECIFIED / **executable not verified** |
| `sports.mlb_innings_stats` | mlb innings stats | SPECIFIED / **executable not verified** |
| `sports.mlb_pitcher_hitter` | mlb pitcher hitter | SPECIFIED / **executable not verified** |
| `sports.mlb_strike_zone_diagram` | mlb strike zone diagram | SPECIFIED / **executable not verified** |
| `sports.mlb_offseason_planner` | mlb offseason planner | SPECIFIED / **executable not verified** |
| `sports.nba_possession_metrics` | nba possession metrics | SPECIFIED / **executable not verified** |
| `sports.nba_tactics_visualizer` | nba tactics visualizer | SPECIFIED / **executable not verified** |
| `sports.soccer_xg_provenance` | soccer xg provenance | SPECIFIED / **executable not verified** |
| `sports.soccer_formations` | soccer formations | SPECIFIED / **executable not verified** |

### CAREER — 7 engine declarations

| Engine ID | Planned purpose | Historical registry status |
|---|---|---|
| `career.labor_demand_radar` | labor demand radar | SPECIFIED / **executable not verified** |
| `career.salary_context_validator` | salary context validator | SPECIFIED / **executable not verified** |
| `career.skill_graph` | skill graph | SPECIFIED / **executable not verified** |
| `career.credential_verifier` | credential verifier | SPECIFIED / **executable not verified** |
| `career.practical_project_lab` | practical project lab | SPECIFIED / **executable not verified** |
| `career.interview_resume_coach` | interview resume coach | SPECIFIED / **executable not verified** |
| `career.career_risk_reviewer` | career risk reviewer | SPECIFIED / **executable not verified** |

### PRODUCTIVITY — 7 engine declarations

| Engine ID | Planned purpose | Historical registry status |
|---|---|---|
| `productivity.workflow_recorder` | workflow recorder | SPECIFIED / **executable not verified** |
| `productivity.bottleneck_finder` | bottleneck finder | SPECIFIED / **executable not verified** |
| `productivity.automation_planner` | automation planner | SPECIFIED / **executable not verified** |
| `productivity.before_after_evaluator` | before after evaluator | SPECIFIED / **executable not verified** |
| `productivity.template_designer` | template designer | SPECIFIED / **executable not verified** |
| `productivity.tool_comparator` | tool comparator | SPECIFIED / **executable not verified** |
| `productivity.habit_evidence_reviewer` | habit evidence reviewer | SPECIFIED / **executable not verified** |

### CULTURE — 7 engine declarations

| Engine ID | Planned purpose | Historical registry status |
|---|---|---|
| `culture.trend_origin_tracker` | trend origin tracker | SPECIFIED / **executable not verified** |
| `culture.diffusion_map` | diffusion map | SPECIFIED / **executable not verified** |
| `culture.cultural_context_analyzer` | cultural context analyzer | SPECIFIED / **executable not verified** |
| `culture.myth_misinformation_critic` | myth misinformation critic | SPECIFIED / **executable not verified** |
| `culture.creator_attribution_rights` | creator attribution rights | SPECIFIED / **executable not verified** |
| `culture.harassment_privacy_gate` | harassment privacy gate | SPECIFIED / **executable not verified** |
| `culture.internet_story_director` | internet story director | SPECIFIED / **executable not verified** |

## Appendix B — 18 original v3 video creative operations

| Operation | Name | Intent and rule | Original spec status |
|---|---|---|---|
| CV3-01 | `BRIEF` | Provenance-aware question and original angle; reject unrelated or near-duplicate video concept. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-02 | `CLAIM_LOCK` | Freeze permitted factual claims; missing critical source blocks production. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-03 | `DOMAIN_STYLE` | Load real domain visual/voice rules; no generic theme swap or disabled domain. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-04 | `BEAT_PLAN` | Ask/promise, evidence, uncertainty, payoff, and duration ranges; mark claims by ID. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-05 | `SHOT_PLAN` | Visual class, permitted source, image/video overlay, speech cue, motion, source & rights dependencies. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-06 | `RIGHTS_CHECK` | Delegate adjudication to existing rights service, unknown legal basis -> HOLD. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-07 | `SOURCE_CLIP_REVIEW` | Require real new independent critique and source-to-commentary link. No generic green-screen license. When source clips are absent, record NOT_APPLICABLE as a durable guard result; downstream stages must not treat a skipped required guard as approval. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-08 | `ASSET_BUILD` | Generate original diagrams or use authorized assets; GPU only if tested/available. Mandatory clip-review guard returns signed NOT_APPLICABLE if no third-party clips; otherwise requires reviewed ReactionClipMap. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-09 | `SPEECH_BUILD` | Synth/import voice, measure speech segment duration and align real timing. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-10 | `LOCALE_BUILD` | Meaning-preserving adaptation, region-safe numbers/names; regenerate text/audio/timing. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-11 | `TEXT_OVERLAYS` | Native-script caption and semantic text tracks; collision, safe box and contrast checks. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-12 | `AUDIO_MIX` | Track-based mix, speech-first intelligibility, loudness evidence and rights. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-13 | `TIMELINE` | Immutable half-open millisecond interval graph, source/rights hashes, scene continuity. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-14 | `RENDER` | CPU FFmpeg or optional GPU provider, reproducible render manifest and bounded retry. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-15 | `TECHNICAL_QC` | Frame/audio/aspect/safe-zone/caption/source/factual validity checks. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-16 | `HUMAN_PREVIEW` | Manual full watch-through; content-specific acceptance, material edits void approval. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-17 | `EXPORT_PUBLISH` | Private export always supported; upload only after correct credentials/policy. Studio dubbing manual handoff. | SPECIFIED_NOT_IMPLEMENTED |
| CV3-18 | `OWN_ANALYTICS` | Use actual owner observations only, compare matched cohorts with uncertainty. | SPECIFIED_NOT_IMPLEMENTED |

## Appendix C — Automation DAG states, 9 triggers and 15 pipeline stages

**States:** `QUEUED`, `RUNNING`, `RETRY_WAIT`, `BLOCKED`, `WAITING_FOR_APPROVAL`, `WAITING_FOR_CAPABILITY`, `SUCCEEDED`, `FAILED`, `CANCELLED`.

**Trigger declarations:**

- `TR-001` — `scheduled_discovery`; event `owner_enabled_poll_window`; schedule `OWNER_CONFIGURED_NO_FORCED_CADENCE`; requires permitted_connector, quota_budget.
- `TR-002` — `live_sports_revision`; event `permitted_provider_new_score_version`; schedule `EVENT_DRIVEN`; requires verified_source_version.
- `TR-003` — `topic_research`; event `approved_or_auto_low_risk_topic_decision`; schedule `EVENT_DRIVEN`; requires topic_id, channel_policy.
- `TR-004` — `draft_production`; event `research_sufficient_for_draft`; schedule `EVENT_DRIVEN`; requires claim_links, rights_plan.
- `TR-005` — `editorial_review`; event `gates_complete_or_sensitive`; schedule `EVENT_DRIVEN`; requires current_risk_snapshot, technical_QA.
- `TR-006` — `upload`; event `approved_publish_intent`; schedule `OWNER_AUTHORIZED_TIME`; requires channel_oauth, content_hash_approval, no_rights_gaps, visibility_permission.
- `TR-007` — `analytics_import`; event `publication_confirmed_and_owner_auth`; schedule `OWNER_CONFIGURED_POST_PUBLISH_WINDOWS`; requires owner_oauth, analytics_scope.
- `TR-008` — `source_correction`; event `source_version_changed_or_correction`; schedule `EVENT_DRIVEN`; requires source_version_id, dependent_edges.
- `TR-009` — `capability_arrived`; event `gpu_worker_heartbeat_capability_change`; schedule `EVENT_DRIVEN`; requires model_license, driver_benchmark, free_vram.

**Pipeline sequence:**

- `01_QUALIFY_SOURCES` — ``
- `02_DISCOVER_TOPIC` — ``
- `03_RESEARCH_PLAN` — ``
- `04_GATHER_EVIDENCE` — ``
- `05_VERIFY_CHALLENGE` — ``
- `06_SCRIPT_STORYBOARD` — ``
- `07_LICENSE_ASSET` — ``
- `08_COMPUTE_RESERVE` — ``
- `09_RENDER` — ``
- `10_TECH_FACT_RIGHTS_QA` — ``
- `11_OWNER_APPROVAL` — ``
- `12_EXPORT` — ``
- `13_PUBLISH` — ``
- `14_ANALYTICS` — ``
- `15_LEARN` — ``

## Appendix D — Real source archive inventory (12 November 2026)

**Source:** `ViralOS_Launch_M2_2_M3_v0_5_Working_Source.zip`. Static code inventory only. A module/route listed here may still be disabled or mock-only; review its code and prerequisites.

### Executable Python modules

| Module | Lines in archived file |
|---|---:|
| `__init__.py` | 1 |
| `creative_m22.py` | 281 |
| `db.py` | 67 |
| `director_m21.py` | 343 |
| `expansion.py` | 334 |
| `intelligence.py` | 85 |
| `main.py` | 365 |
| `renderer.py` | 106 |
| `source_connectors.py` | 58 |
| `studio_contracts.py` | 81 |
| `studio_render.py` | 318 |
| `studio_routes.py` | 250 |
| `tts.py` | 34 |
| `youtube_analytics.py` | 72 |
| `youtube_private.py` | 176 |

### SQL migrations

- `001_schema.sql`
- `002_controls.sql`
- `003_creative.sql`
- `004_m1_m3.sql`
- `005_studio.sql`
- `006_m21_director.sql`
- `007_m22_creative.sql`
- `008_m3_publishing.sql`

### Automated test modules

- `test_launch.py`
- `test_m1_m3.py`
- `test_m21_director.py`
- `test_m22_m3_private.py`
- `test_m2_studio.py`

### Actual decorated API routes in that archive

| Method | API path | Source file |
|---|---|---|
| `GET` | `/api/m22/creative-policies` | `creative_m22.py` |
| `GET` | `/api/m22/final-exports/{export_id}/download` | `creative_m22.py` |
| `GET` | `/api/projects/{project_id}/m22/creative-audit/{render_id}` | `creative_m22.py` |
| `POST` | `/api/projects/{project_id}/m22/plans/{plan_id}/words` | `creative_m22.py` |
| `GET` | `/api/projects/{project_id}/m22/plans/{plan_id}/words.vtt` | `creative_m22.py` |
| `POST` | `/api/projects/{project_id}/m22/reviews/{review_id}/export-final` | `creative_m22.py` |
| `POST` | `/api/projects/{project_id}/m22/studio/renders/{render_id}/review-final` | `creative_m22.py` |
| `GET` | `/api/director/capabilities` | `director_m21.py` |
| `POST` | `/api/projects/{project_id}/director/drafts` | `director_m21.py` |
| `GET` | `/api/projects/{project_id}/director/drafts/{draft_id}` | `director_m21.py` |
| `POST` | `/api/projects/{project_id}/director/drafts/{draft_id}/assemble` | `director_m21.py` |
| `POST` | `/api/projects/{project_id}/director/drafts/{draft_id}/synthesize-piper` | `director_m21.py` |
| `POST` | `/api/projects/{project_id}/director/drafts/{draft_id}/voice/{segment_index}` | `director_m21.py` |
| `GET` | `/api/projects/{project_id}/director/plans/{plan_id}/captions.srt` | `director_m21.py` |
| `POST` | `/api/analytics/owner-entry` | `expansion.py` |
| `GET` | `/api/analytics/{channel_id}` | `expansion.py` |
| `POST` | `/api/projects/{project_id}/bind-source` | `expansion.py` |
| `GET` | `/api/projects/{project_id}/captions/{locale}` | `expansion.py` |
| `POST` | `/api/projects/{project_id}/export-review-packet` | `expansion.py` |
| `POST` | `/api/projects/{project_id}/feeds/sync/{feed_key}` | `expansion.py` |
| `POST` | `/api/projects/{project_id}/locales` | `expansion.py` |
| `GET` | `/api/projects/{project_id}/quality-report` | `expansion.py` |
| `GET` | `/api/projects/{project_id}/research-audit` | `expansion.py` |
| `POST` | `/api/projects/{project_id}/review-video` | `expansion.py` |
| `POST` | `/api/projects/{project_id}/rss-import` | `expansion.py` |
| `POST` | `/api/projects/{project_id}/story-plan` | `expansion.py` |
| `GET` | `/api/projects/{project_id}/story-plan` | `expansion.py` |
| `POST` | `/api/projects/{project_id}/voice/opt-in-piper` | `expansion.py` |
| `GET` | `/api/research/approved-feeds` | `expansion.py` |
| `GET` | `/api/review-packets/{export_id}` | `expansion.py` |
| `GET` | `/api/voice/piper-capabilities` | `expansion.py` |
| `POST` | `/api/youtube/analytics/sync` | `expansion.py` |
| `GET` | `/api/youtube/capabilities` | `expansion.py` |
| `POST` | `/api/youtube/upload` | `expansion.py` |
| `GET` | `/` | `main.py` |
| `GET` | `/api/capabilities` | `main.py` |
| `GET` | `/api/channels` | `main.py` |
| `POST` | `/api/channels` | `main.py` |
| `POST` | `/api/claims/{claim_id}/review` | `main.py` |
| `GET` | `/api/editions` | `main.py` |
| `GET` | `/api/jobs` | `main.py` |
| `POST` | `/api/jobs/run-next` | `main.py` |
| `POST` | `/api/jobs/{job_id}/retry` | `main.py` |
| `GET` | `/api/previews/{render_id}` | `main.py` |
| `GET` | `/api/projects` | `main.py` |
| `POST` | `/api/projects` | `main.py` |
| `GET` | `/api/projects/{project_id}` | `main.py` |
| `POST` | `/api/projects/{project_id}/claims` | `main.py` |
| `POST` | `/api/projects/{project_id}/queue-preview` | `main.py` |
| `POST` | `/api/projects/{project_id}/scenes` | `main.py` |
| `POST` | `/api/projects/{project_id}/script` | `main.py` |
| `POST` | `/api/projects/{project_id}/sources` | `main.py` |
| `POST` | `/api/projects/{project_id}/voice` | `main.py` |
| `GET` | `/health` | `main.py` |
| `GET` | `/api/projects/{project_id}/studio/assets` | `studio_routes.py` |
| `POST` | `/api/projects/{project_id}/studio/assets/music` | `studio_routes.py` |
| `POST` | `/api/projects/{project_id}/studio/assets/still` | `studio_routes.py` |
| `GET` | `/api/projects/{project_id}/studio/example` | `studio_routes.py` |
| `GET` | `/api/projects/{project_id}/studio/plan` | `studio_routes.py` |
| `POST` | `/api/projects/{project_id}/studio/plans` | `studio_routes.py` |
| `POST` | `/api/projects/{project_id}/studio/queue` | `studio_routes.py` |
| `GET` | `/api/projects/{project_id}/studio/renders` | `studio_routes.py` |
| `GET` | `/api/studio/capabilities` | `studio_routes.py` |
| `GET` | `/api/studio/previews/{render_id}` | `studio_routes.py` |
| `GET` | `/api/studio/reports/{render_id}` | `studio_routes.py` |
| `POST` | `/api/studio/run-next` | `studio_routes.py` |
| `GET` | `/api/m3/private-upload/capabilities` | `youtube_private.py` |
| `POST` | `/api/m3/private-upload/intents` | `youtube_private.py` |
| `GET` | `/api/m3/private-upload/intents/{intent_id}` | `youtube_private.py` |
| `POST` | `/api/m3/private-upload/intents/{intent_id}/execute` | `youtube_private.py` |

**Important external evidence:** archive build report `ViralOS_M2_2_M3_BUILD_REPORT.json`: 51 local automated tests, Linux FFmpeg/FFprobe pytest, synthetic eSpeak narration. `live_youtube_oauth_upload_tested=false`, `live_youtube_analytics_tested=false`, `windows_i7_8thgen_32gb_tested=false`, `natural_quality_voice_tested=false`, `live_gpu_tested=false`, `public_auto_publish=false`. Preserve these booleans until newer evidence overrides them.


## Appendix E — v2.2 exact 25 audiovisual gap register (historical specification)

| ID | Missing/underspecified capability | Intended owner | Gate |
|---|---|---|---|
| CP-001 | Audience promise and narrative beats tied to timed evidence/visual timeline | `creative/narrative_director` | Each key beat has purpose, facts, payoff and shots |
| CP-002 | Typed `VideoTimeline`, lanes, transitions, compositing, safe zones | `creative/timeline_compiler` | deterministic scene duration/overlap test |
| CP-003 | Overlay animation geometry/typography and text hierarchy | `creative/overlay_director` | mobile legibility, occlusion and glyph test |
| CP-004 | Word/phrase narration alignment and subtitle profiles | `creative/speech_alignment` | measured speech-to-caption sync |
| CP-005 | Region-localization package with dubbing, text, graphics and title versions | `localization/variant_builder` | locale review and no source-claim mutation |
| CP-006 | Human review for names, quotes, idioms, native terms and AI-dub errors | `localization/linguistic_qc` | approval before exporting sensitive locale |
| CP-007 | Speech style, pronunciations, voice identity rights and mixing | `audio/voice_director` | pronunciation and intelligibility listening test |
| CP-008 | Music/SFX selection, sidechain ducking and audio rights | `audio/sound_director` | rights and loudness QA |
| CP-009 | Third-party clip rights, reuse originality, and official remix status | `media/clip_rights_adjudicator` | BLOCK until lawful basis and independent monetization review |
| CP-010 | Clip transcript/context, critique mapping, source link, substantive transformation | `creative/commentary_clip_director` | owner review of actual transformed output |
| CP-011 | Category-specific VIDEO director profiles, not just research playbooks | `domains/*/visual_policy` | 12 visual golden samples |
| CP-012 | Format grammar: news brief / sports reaction / lesson / documentary / review | `creative/format_director` | at least one approved sample each |
| CP-013 | Visual coverage ratio: shot backed by spoken claim/context, not random stock b-roll | `creative/evidence_visual_matcher` | unsupported illustrative-shot flag |
| CP-014 | Vertical and horizontal reframe with faces, scoreboards and subtitles | `creative/reframe_director` | device viewport safe zone snapshot QA |
| CP-015 | Prompt-to-asset fallback for CPU now; GPU/video generation later | existing `compute + creative/prompt_compiler` | no unsupported claim of photorealistic output |
| CP-016 | Fact/correction dependency chain across every locale & render variant | existing `evidence/invalidator` | corrected fact invalidates localized dubbing/overlays |
| CP-017 | Scene-by-scene engagement diagnostics and creative hypothesis registry | `audience/creative_lab` | only observed analytics; control for uncertainty |
| CP-018 | Storytelling ending and next-video handoff, platform end screens | `creative/ending_director` | payoff answered, outro not deceptive |
| CP-019 | Explicit video-level content novelty assessment across channels | existing `audience/portfolio` | near-duplicate review; no mass templating |
| CP-020 | Distinct `audio-language track` vs localized separate videos strategy | `publishing/localization_adapter` | account feature capability check; no imaginary API endpoint |
| CP-021 | Accessibility: caption readability, color contrast, audio description needs | `creative/accessibility_qc` | sample caption/audio review |
| CP-022 | Clip remix attribution and original deletion/restriction lifecycle | `publishing/remix_status_tracker` | manual/source-tool status and update notice |
| CP-023 | Audio-video render approval by full watch-through, not just ffprobe | `creative/editorial_preview` | owner approves actual final file |
| CP-024 | Source-led shot storyboard not derivable from a single generic prompt | `creative/shot_director` | each shot has evidence/illustration class |
| CP-025 | Detailed release/profile feature flags prevent partial v2.2 from being claimed implemented | `core/release_controller` | feature is SPECIFIED until tested |

## Appendix F — Historical source artifacts and confidence

- **Original requirements (historical):** `ViralOS_Launch_Edition.md`, `ViralOS_Ultimate_Edition.md`, `ViralOS_Launch_AgentReady_v2.md`, `ViralOS_Ultimate_AgentReady_v2.md`.
- **Independent gap/reality audit:** `ViralOS_Verified_Reality_Audit_2026-11-09.md` (proved 144 registry entries ≠ 144 functional agents), `ViralOS_Content_Production_Audit_and_Master_Playbook_v2_2.md` (25 CP gaps).
- **Architecture/benchmark evidence:** `03_FINAL_ARCHITECTURE_DECISION_ADR-001.md`, `04_IMPLEMENTATION_AND_VALIDATION_PLAN.md`, `01_PLATFORM_COMPETITOR_STUDY.md`, `02_120_CHANNEL_CONTENT_BENCHMARK.md`, `120_channel_benchmarks.csv`, `ViralOS_Competitor_and_120_Channel_Research_2026-11-09.zip`.
- **v3 contracts:** `ViralOS_Launch_v3.zip`, `ViralOS_Ultimate_v3.zip`, `ViralOS_Combined_v3.zip` including creative matrix, execution registries, workflow DAG, API and schema specs.
- **Archived code proof:** `ViralOS_Launch_Implementation_M0.zip`, `ViralOS_Launch_M2_Studio_v0_3_Working_Code.zip`, `ViralOS_M2_1_Working_Source.zip`, `ViralOS_Launch_M2_2_M3_v0_5_Working_Source.zip`, accompanying demo MP4/PNG/QC reports and build JSON.
- **Historical later continuation:** project conversation summaries 15–20 November 2026. They confirm ongoing discussion and priority intents but not independently accessible source artifacts for late phases.

**No GitHub contact or source synchronization was undertaken to prepare this handoff.**
