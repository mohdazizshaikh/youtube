# Phase 12 — opt-in private editorial browser console

This console is a separate local FastAPI process, not an internet-facing service and not a new upload route in the existing Studio. It connects the Phase 9 media audit, Phase 10 review packets and Phase 11 SQLite ledger. It is deliberately disabled unless the operator launches it. It does not create drafts, authenticate reviewers, establish truth/rights, or authorize publication.

## Setup on the owner machine

Install the existing repository requirements and local FFmpeg/ffprobe. Keep the queue, catalog and all media in owner-controlled directories **outside the source tree**; on Windows use owner-only NTFS permissions. Use an existing queue or initialize a new one with the Phase 11 command (never initialize over an existing database):

```powershell
python -m tools.domain_review_queue init --db C:\ViralOSPrivate\reviews.sqlite
(Get-FileHash -Algorithm SHA256 C:\ViralOSPrivate\job\draft\manifest.json).Hash.ToLowerInvariant()
```

The manifest pin must come from the original trusted draft receipt or be confirmed by the owner against that receipt. Computing a hash from an unknown/untrusted manifest does not authenticate it. Create `C:\ViralOSPrivate\catalog.json` as an array of 1–100 unique entries, each containing exactly these fields (replace the example pin with the confirmed 64-character lowercase hash; JSON uses escaped backslashes):

```json
[
  {
    "manifest_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "draft": "C:\\ViralOSPrivate\\job\\draft",
    "assets": "C:\\ViralOSPrivate\\job\\assets"
  }
]
```

From the repository root:

```powershell
python -m tools.domain_review_web --db C:\ViralOSPrivate\reviews.sqlite --catalog C:\ViralOSPrivate\catalog.json --port 8765
```

Open `http://127.0.0.1:8765/` in your local browser. The server binds only to literal IPv4 loopback, disables proxy headers/access logging, and uses the existing Host/Origin/Fetch-Metadata guard plus an ephemeral session header. Stop with Ctrl+C. Do not expose it through a reverse proxy, tunnel or LAN binding. The session header is an anti-cross-origin safeguard, **not authentication against another local process**.

## Review workflow

1. Register an unregistered configured draft (fresh technical media audit). Existing queue registrations are reusable.
2. Open a registered draft; a new technical audit rebuilds the review packet and checks its hash against the queue registration. The console displays the declared scene times, titles, narration, source and specialist evidence. Source text is rendered as text, not executable markup or clickable remote content.
3. Load the pinned MP4. The console hashes the actual bytes before returning those same bytes; video size is bounded to 128 MiB. The browser plays the local Blob. Review every scene against the actual material and independently obtained primary sources. The technical audit does not check every word or frame. No remote site is fetched automatically.
4. Enter your reviewer declaration and choose NOT_REVIEWED, PASS or REVISE for every required check. A scene with REVISE must have a revision note. Submit explicitly; the server re-audits and checks the packet and optimistic revision. Stale, duplicate and tampered submissions fail; reopen the current draft to load a new revision. Never blindly overwrite another review.
5. Inspect the recorded status and revision history. `SELF_ATTESTED` is still only a local declaration; `DEMO_BLOCKED` applies to synthetic inputs. There is no publication permission. Names and notes are not stored in the queue, so preserve your own private reviewer record if needed. Do not share browser screenshots of private material. Close the console after review; browser/OS memory and local processes are outside this privacy boundary.

## Implementation boundaries and validation

The API takes pins, not paths. Catalog paths are startup-only and outside the repository; status/history are scoped to the configured pins. Session headers are required on all API routes. No-store, CSP, frame-denial and nosniff headers reduce browser leakage/embedding risk; no browser storage or remote dependencies are used. Expensive audit/video operations are serialized in the single process, and JSON submissions are capped at 128,000 bytes. Local directories are assumed owner-controlled and not concurrently modified by hostile processes. The ledger is not signed, and the audit is not proof of factual, legal or reviewer authenticity.

Automated API tests cover authentication-boundary checks (not user authentication), startup validation, fixed catalog scope, registration, re-audit, pinned media bytes, stale revision, review privacy, strict request shape and bounds, synthetic blocking and real FFmpeg tampering. JavaScript syntax was checked with Node. A separate actual loopback Uvicorn HTTP smoke run using a Phase 9 synthetic business draft passed registration, fresh packet generation, exact MP4 byte retrieval and a synthetic all-pass checklist submission that remained DEMO_BLOCKED. This was native HTTP, not browser playback. The headless Chromium browser smoke attempt was blocked by the environment's administrator policy on localhost navigation; interactive browser playback, accessibility and owner Windows UI acceptance have not been established. Use the manual workflow above to test on the owner machine before use.
