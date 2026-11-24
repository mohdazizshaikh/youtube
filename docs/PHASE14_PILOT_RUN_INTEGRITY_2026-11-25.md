# Phase 14 — stopped pilot-run integrity and resume preflight

Baseline: Phase 13 commit `e01f1b7e6e40f61cd2ed3553b0daa923a7a04cc5`. This additive candidate is deliberately independent of the existing launcher; no migration, automatic upload, or publishing authority.

Stop the review console before verification. Record the exact manifest SHA-256 from a trusted completed run separately, outside the run folder. Do not derive your trusted pin from an untrusted restored receipt. From the repository root:

```
python -m tools.pilot_run_verify --run /private/run --manifest-sha256 YOUR_TRUSTED_SHA256
```

Default mode repeats the existing independent media and packet audit after metadata, exact inventories, hashes, template, catalog, and read-only SQLite queue checks. `--metadata-only` skips media decode and is suitable only for technical inspection. Any failure means do not resume; retain evidence and rebuild or reconcile manually. The check rejects moved catalogs rather than rewriting absolute paths. Run in an owner-controlled directory on a stopped process; it is not a sandbox against concurrent hostile filesystem writes. On Windows, reparse points at inspected paths are blocked. It does not check every ancestor's ACL or prove the identity of a human reviewer, validate real voice licensing, or grant publishing permission. The CLI emits only bounded status and exception type, never local path or review text.

The new synthetic contract suite includes 73 parameterized cases (count by pytest collection), not 73 completed features. The fixture media is placeholder bytes; the fresh media branch needs existing FFmpeg integration and a real pilot run. Full CI and owner machine acceptance are pending at authoring. No owner data or account action.

Next: prove stopped-run preflight on a real Phase 13 pilot, integrate the Windows resume wrapper only after that succeeds, and conduct supervised owner recovery and native playback. Preserve Phase 13 fallback.
