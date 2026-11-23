# ViralOS migration verification — 23 November 2026

## Target and scope

- Target: `https://github.com/mohdazizshaikh/youtube`, branch `main`.
- All transferred material came from locally available project snapshots and historical deliverables. The suspended former GitHub account was **not contacted**.
- Source application: **M2.2 + M3 PRIVATE v0.5 snapshot from 12 Nov 2026**; no representation that changes from 13–20 Nov are present without recovered source evidence.
- Original recovery assets are in `recovery/original-artifacts/`; requirements, tests, app, SQL migration lineage (001–008), Launch/Combined v3 design documents and handoff are in their normal paths.

## Independent hash check

Before this verification note and CI workflow were added, a complete comparison of **584 locally reconstructed files** against all **584 GitHub `main` blobs** was performed on commit `b99f28c38bbdcf3b982e082ebd7e387a19425d53`:

- GitHub reported an untruncated recursive tree of 584 blobs.
- Local and GitHub file sizes summed to **18,768,899 bytes**.
- Every `(path, Git blob SHA-1)` entry matched. Independent sorted-path FNV-1a-64 digest: **`084a058f93159222`** on both sides.
- The 32 original historical artifacts are catalogued with SHA-256 in `recovery/ORIGINAL_ARCHIVE_INDEX.md`; provenance is additionally recorded in `recovery/PROVENANCE_MANIFEST.json`.

This is a byte-for-byte comparison **against the assembled local recovery package**, *not* a comparison with the unavailable former remote.

## Re-run checks

- `python -m pytest -q`: **51 passed** (Linux container, Python 3.13, 23 Nov 2026).
- `python tools/verify_package.py`: **PASS — 280 package file hashes**.
- `node --check app/static/app.js`: **PASS**.
- `python -m compileall -q app tools tests`: **PASS**.
- A new `.github/workflows/cpu-baseline.yml` repeats these checks on GitHub Actions for future changes; **CI job status is not asserted here**.

## Not demonstrated / remaining engineering gates

1. Recover any newer (13–20 Nov 2026) code or Git history from **owner-supplied offline backups only**.
2. Perform clean installation, backups, failure/restart and render review on the original Windows i7 8th-gen / 32 GB / no dedicated GPU computer.
3. M2.4: professional offline voices, genuine automatic word alignment, scene-level Hindi/English dubbing, pronunciation rules and localized graphics.
4. M3.2: supervised, owner-authorized **PRIVATE** upload on the real YouTube channel; verify OAuth, analytics/permissions, rollback, duplication and quota failure behavior.
5. Finish evidence/rights/originality and user-approval acceptance; benchmark 12 specialized domains and 144 *designed* engines before marking executable.
6. Test actual GPU/video-model portability, quality, production benchmarks and revenue reports only when hardware/accounts/clearances are available.

**Restriction:** never assume this repository restores the previous suspended account's unreachable commits. Never automatically enable PUBLIC publishing or commit credentials, private data, unlicensed media or API secrets.
