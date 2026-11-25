# Phase 14B — pilot snapshot, restore and preflight

Prior Phase 14 commit `a4eba5d5c8a52edc39d66b4ff7deaab7060ece2c`: GitHub Actions run 45500025508 completed successfully on Linux CPU and Windows contracts, including package hashes and 73 portable test cases. This new increment remains a candidate until its own CI and actual owner acceptance.

Stop the pilot console first. Use an ordinary owner-controlled local directory outside source and outside synced folders. Protect permissions; directory mode 0700 is not a Windows ACL configuration. Keep both trusted pins separately from the backup itself. No credentials, OAuth tokens, application DB, or undeclared files are included.

```
python -m tools.pilot_snapshot backup --run /private/run --output /private/snapshot --manifest-sha256 TRUSTED_RUN_PIN
python -m tools.pilot_snapshot verify --snapshot /private/snapshot --snapshot-sha256 TRUSTED_SNAPSHOT_PIN --manifest-sha256 TRUSTED_RUN_PIN
python -m tools.pilot_snapshot restore --snapshot /private/snapshot --output /private/restored --snapshot-sha256 TRUSTED_SNAPSHOT_PIN --manifest-sha256 TRUSTED_RUN_PIN
```

The snapshot is a directory, not an encrypted archive. The verify subcommand checks hashes only, not media decode. Backup and restore require fresh independent media audit, exact bounded inventory, copied SHA-256 and byte lengths, matching queue state/revision, and no overwrite. Restore deliberately rewrites only the absolute-path catalog for the new directory. Failed operations preserve partial evidence with an INCOMPLETE marker; do not use such directories. Backup must be performed with console stopped; concurrent hostile filesystem mutations and sudden power loss are outside the guarantees. Snapshot manifest hashes protect integrity only when trusted separately; they are not signatures. Keep offline copies in separate owner-controlled storage. No automatic deletion.

Start-Pilot now prints the trusted newly created pin; Resume-Pilot requires the separately recorded pin and both invoke the fresh preflight before launching the review web server. Existing Phase 13 runs with a trusted pin remain usable; owner must not treat a pin extracted from a suspected run as trusted. Windows launcher integration is a candidate, not physical device acceptance.

New coverage: portable snapshot validation/tamper/revision tests, and one FFmpeg-generated synthetic pilot roundtrip with fresh audits. Fixtures are not actual owner media. No review, model license, real YouTube upload or publication permission is conferred.
