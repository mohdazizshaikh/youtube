# Phase 11 — local durable editorial review queue

Phase 10 packets can now be tracked in a separate SQLite ledger. Each draft is registered only after the Phase 9 technical audit and Phase 10 packet reconstruction. The immutable registration binds the external manifest SHA-256, canonical packet hash, video hash, domain, format and synthetic-demo classification. Multiple draft versions may coexist under different manifest hashes.

## Operator workflow (local, offline)

Keep the database, draft media and reviewer documents in an owner-controlled directory outside the public repository. On Windows configure owner-only NTFS permissions; on POSIX the newly created database uses mode 0600. Do not commit reviewer material or database snapshots. Example commands from the repository root, replacing paths and pins with the real values:

```text
python -m tools.domain_review_queue init --db /private/reviews.sqlite
python -m tools.domain_review_queue register --db /private/reviews.sqlite --draft /private/job/draft --assets /private/job/assets --manifest-sha256 <pin>
python -m tools.domain_draft_review prepare --draft /private/job/draft --assets /private/job/assets --manifest-sha256 <pin> --output /private/review-packet.json
python -m tools.domain_review_queue status --db /private/reviews.sqlite
python -m tools.domain_review_queue submit --db /private/reviews.sqlite --draft /private/job/draft --assets /private/job/assets --manifest-sha256 <pin> --expected-revision 0 --review /private/completed-review.json
```

Prepare the completed review JSON from the `review_template` section of the private packet, following the Phase 10 guide. Every submission reruns the technical audit, rejects stale or changed packet pins and requires the current queue revision. Reload `status` before retrying a stale submission. Resubmission of an identical review is rejected. Concurrent writers serialize via SQLite transactions; a submitted revision and its history record commit together or roll back together. A crash before commit leaves the prior revision intact. No network access is involved.

States: `PENDING`, `INCOMPLETE`, `NEEDS_REVISION`, `DEMO_BLOCKED`, `SELF_ATTESTED`. `DEMO_BLOCKED` is mandatory for synthetic demos regardless of declarations. `SELF_ATTESTED` means only that the owner-supplied checklist passed the local contract, not that any factual, legal, speaker or reviewer claims were independently verified. The queue does not create a publication permission, change YouTube state or alter the main application database. Status is a historical snapshot, not a fresh media audit; re-audit before any downstream decision. The queue database is not signed or tamper-evident against someone with filesystem access.

The ledger stores only hashes, domain/format, synthetic classification, scene and blocker counts, revision/state history. No raw names, notes, script text, media paths or credentials are persisted. Hashes may still correlate private artifacts. Keep status exports private as well. This is a local CLI workflow, not a multi-user authenticated service or an autonomous editorial director.

## Validation

Tests cover exclusive initialization, refusal to use an unrelated SQLite DB, repeat registration, stale/replayed submission rejection, concurrent revisions, private notes exclusion, demo blocking, incomplete/revision/self-attested states and real FFmpeg media re-audit with tampered captions. Actual independent human acceptance remains pending.
