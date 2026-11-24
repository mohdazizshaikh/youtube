# Phase 10 — pinned editorial review handoff

The Phase 9 technical media auditor is now connected to a local scene-by-scene human review packet. This is a preparation and self-attestation workflow, not a production release gate. Nothing is sent to a remote service.

## Prepare a review

Use the SHA-256 of the original approved technical draft manifest from a trusted local delivery record (not a fresh hash of an untrusted replacement). Run from the project root:

```sh
python -m tools.domain_draft_review prepare --draft /path/to/draft --assets /path/to/assets --manifest-sha256 <pinned-sha256> --output /private/review-packet.json
```

The command reruns media checks and exports each scene's source links/locators, claims, specialist fields, timestamps, narration text and hashes. Review the actual full video, sources, disclosures, narration, captions, rights and originality. Copy the `review_template` object to a separate private JSON file; fill in the reviewer declaration, set each check to `PASS`, `REVISE` or `NOT_REVIEWED`, and supply notes for revisions. Never store private notes or source license documents in the public Git repository. Keep the source inputs immutable during review; no process isolation or authenticated reviewer identity is provided.

```sh
python -m tools.domain_draft_review evaluate --draft /path/to/draft --assets /path/to/assets --manifest-sha256 <pinned-sha256> --review /private/completed-review.json --output /private/review-result.json
```

An evaluation reruns technical audit, rebuilds the review packet and validates exact scene coverage and fingerprints. A changed draft or stale review is rejected. Exit code 2 means checklist incomplete or a synthetic demo, 0 means the manual checklist is complete for a declared non-synthetic draft. Even then `publication_eligible` is always false. The result omits reviewer name and notes; its review hash is a local content identifier, not a digital signature. Notes remain in the private input. There is no upload endpoint or integration into existing private upload approval.

## Prepare all 24 domain-format drafts

Use an independently retained hash of the original batch `index.json`:

```sh
python -m tools.domain_review_batch --root /path/to/phase9-drafts --index-sha256 <pinned-index-sha256> --output /private/review-packets
```

The batch validates exactly 12 domains × two formats, rejects unexpected paths and duplicate records, reruns media audit for each draft and binds the manifest/video identities. The output directory must not exist. On caught failure the newly created output directory is removed. Successful output contains 24 packet/template JSON files and one index, with zero human reviews completed. It does not mark synthetic examples as accepted films. It does not authenticate source facts, rights, voice identity or reviewer competence. Retain real data outside this public repository.
