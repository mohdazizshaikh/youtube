# ViralOS — Next engineering recovery increment (24 November 2026)

**Repository:** `mohdazizshaikh/youtube` — only this new account was used. **This is NOT a production acceptance.** The original suspended remote was never accessed. The current runnable historical foundation remains the locally recovered M2.2/M3 archive from 12 November plus later code authored independently.

## What is implemented and testable

| Area | Real changes | What is still missing |
|---|---|---|
| Source recovery | Read-only, no-network `tools/reconcile_owner_backup.py` inventories owner-held ZIP/folder, ignores credential paths, flags changed migrations and never merges automatically | Owner's 13–20 Nov offline snapshot was not found; do not claim reconstructed commit history |
| M2.4/M2.5 localization | `app/localization_review.py`, SQL `010`, UTF-8 Hindi/English/Hinglish variants, glossary, number/dependency checking, mandatory owner review | Real licensed voices, verified translation quality, word-level speaker identity, automatic scene retiming and rebuilt localized MP4 |
| Research/domain depth | `app/domain_adapters.py` has 12 separately typed specialist metadata checklists, source and independence-group checks, distinct domain visual grammars | Real independent fact-checking, real retrieval/ontology engines, 144 executable AI agents, 12 completed category videos |
| Editorial quality | `app/editorial_evidence.py`, SQL `011`, source-claim links, evidence/asset records, immutable owner sign-off tied to **existing M2.2 final-export fingerprint** | Originality judgment, license legal opinion and independent domain expert acceptance; the sign-off is not automatic legal clearance |
| GPU readiness | `app/compute_capabilities.py` validates model manifest/rights/VRAM/adapter flags; CPU routing contract; GPU-only jobs fail closed with no owner-validated device | Actual CUDA inference adapter, GPU device installed/benchmarked, real licensed image/video model, distributed worker execution |
| Audience data | `app/audience_scene_audit.py` maps owner-supplied observed retention values onto scene intervals, reports sampling caveats | Verified OAuth-proven real Analytics data, attribution of a retention change to a creative choice, longitudinal experiments, genuine revenue measurement |
| M3.2 | Existing read-only private-video metadata/account checks remain intact | Actual owner-authorized PRIVATE upload, analytics receipt and Studio verification; no upload was executed from this development environment |
| M4 Windows | Existing PowerShell preflight and SQLite backup/restore remain intact and tested in Linux with fixtures | Run actual Windows i7/32GB installer, Hindi font/audio render QA, restart and restore drill on owner's machine |

## New APIs

`GET /api/domain-adapters` and `POST /api/domain-adapters/{domain}/review-evidence` operate on **metadata supplied in the request**, never on verified external research. Each of the twelve domain types has unique required fields and creative visual grammar.

`GET /api/m25/capabilities`, `POST /api/projects/{id}/m25/localizations`, `GET /api/projects/{id}/m25/localizations/{variant_id}`, and `POST /api/projects/{id}/m25/localizations/{variant_id}/owner-review` create immutable owner-script variants. Source-script and linked evidence fingerprints invalidate variants after changes; numeric conversion notes and owner approval remain mandatory. **No dubbing or video generation occurs here.** Existing older M2 source/locale forms are preserved for compatibility.

`GET /api/projects/{id}/m26/editorial-audit` and `POST /api/projects/{id}/m26/editorial-owner-review` record nonlegal attestations against owner-reviewed final exports. The latter reuses `youtube_private.resolve_export()` so modified voice, media, script, claim/rights evidence, final MP4 or prior approvals fail closed. This is an **additional** review surface, not yet wired to the uploader as a mandatory condition; the uploader's pre-existing M2.2 owner final-video review remains mandatory.

`GET /api/compute/v1/capabilities` and `POST /api/compute/v1/route-dry-run` never run local models; returning a feasible device is only routing metadata, not a GPU test. `POST /api/audience/retention/scene-map` is a noncausal, in-memory analysis of supplied observations; it cannot authenticate the data's source.

## Resume / recovery of owner-held files

**Never attempt to connect to the suspended remote.** Given a personally held local backup, run from an *offline working copy*:

```powershell
.\.venv\Scripts\python.exe tools\reconcile_owner_backup.py --candidate C:\Private\my-viral-os-backup.zip --current-root . --output C:\Private\reconciliation.json
```

The tool writes a local JSON **outside the source tree**; it enumerates added paths and changed filenames, never copies or automatically executes contents. Before selectively reintroducing code, a human must inspect credentials, third-party licenses and migration SHA conflicts, manually apply reviewed changes, run tests, and make a separate signed-off commit. `.env` and known credential paths are omitted from the report.

## Actual owner acceptance plan (blocked external gate)

1. On the real Windows i7/32GB PC, run `tools/windows_acceptance.ps1`; check 16 kHz mono WAV, installed Hindi fonts, Piper license/voice and real offline CTC model.
2. Independently review a complete original Hindi Short and an English long-form render, all word timings, names, pronunciation, layers, audio mix and rights manifest. The M25 metadata does not automatically create these videos.
3. Run local DB backup/verify/restore on a separate clean directory. Never commit the private archive, access tokens or customer/channel data.
4. In the YouTube desktop OAuth flow, authorize only a channel the owner controls. Obtain a separately approved PRIVATE video with the existing uploader (default disabled). After Studio inspection, run `tools/m32_private_acceptance.py` read-only; do not blindly retry `REMOTE_UNKNOWN` upload status.
5. Inspect actual authorized Analytics after publication, record the source/period and map retention to scene IDs as an **observational** hypothesis, not proof of causation.
6. For all 12 domains, produce an original, human-reviewed Short and long form with separate expert and media-rights acceptance; validate GPU capabilities and licensing only on the user's real hardware.

## Regression and release boundary

Execute `python -m pytest -q`, `python tools/verify_package.py`, `node --check app/static/app.js` and `python -m compileall -q app tools tests`. The package hash manifest is regenerated for changed files; the original 12 November hash snapshot remains in `recovery/ORIGINAL_M22_INTEGRITY_MANIFEST.json`. The previous 23 November work remains in Git history.

**Status vocabulary:** `IMPLEMENTED_TESTED_LOCAL` ≠ `LIVE_ACCOUNT_ACCEPTED` ≠ `OWNER_ACCEPTED` ≠ `RELEASED`. Never state 12 full creative operating systems, 144 runnable AI engines, natural local voices, real-account uploads, native Windows acceptance or GPU video generation are complete without the appropriate evidence.
