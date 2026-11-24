# Phase 13 — Production readiness candidate and single-channel pilot

Stable fallback: Phase 12, commit `c21999bab9b4b018edca5f9f250aabb0df052dd6`, GitHub CI run 45385227383 successful. Preserve the archived ZIP and its hash manifest; do not downgrade a live database by copying over it. Phase 13 adds no production DB migration. The new private pilot uses a separate queue database per run.

## Windows 10/11 owner installation

1. Extract the source ZIP into an ordinary user-owned folder, not over an existing deployment. Verify trusted package origin and the SHA-256 manifest. Install trusted Python 3.12 with `py` launcher and FFmpeg/ffprobe on PATH. No global installer or administrator privilege is invoked by these scripts. Ensure local NTFS permissions protect `%LOCALAPPDATA%\ViralOS\Phase13` and media. Do not use a shared or synced folder. The scripts honor PowerShell execution policy; do not bypass an organization's policy.
2. Double-click `Setup-ViralOS.cmd`. It verifies source hashes, creates a new external venv, installs the repository requirements only after explicit `INSTALL` consent, runs pip check and preflight, and records the actual package versions. No dependency installation on normal startup. For an owner-prepared trusted offline wheelhouse instead use `powershell.exe -NoProfile -File tools\phase13_windows.ps1 -Mode Setup -Wheelhouse C:\Private\wheels`. Requirements are ranges, not a reproducible lockfile. If setup partially fails, keep evidence and repair/recreate the venv deliberately; no automatic deletion. Never use an untrusted wheelhouse/index.
3. Extract the separate pilot input ZIP. Double-click `Start-Pilot.cmd`, enter the absolute input directory containing `plan.json` and `assets`, and open `http://127.0.0.1:8765/` after startup. A new private run is created. No existing run is overwritten. Close with Ctrl+C; `Resume-Pilot.cmd` reopens a completed private run. A run with INCOMPLETE marker must not be treated as valid. Rebuild in a new directory rather than deleting evidence. The console uses absolute paths; moving an existing run requires owner reconfiguration and re-audit.
4. Double-click `Run-Acceptance.cmd` to execute the existing synthetic recovery, regression, package, hardware and CPU Studio checks with the same venv. Reports are private and outside the source tree; smoke/test render files may still be created under source outputs. Never run tests against a real production DB. Node is optional for startup but needed for a complete legacy acceptance result. Inspect actual logs and play the full video in the local browser; record owner hardware and UI results, not merely a cloud CI status.

The one-click wrappers are assisted launchers, not a self-contained offline installer. Python, FFmpeg and trusted dependencies must be available; installation, Windows PowerShell execution, native Windows playback, physical i7/32GB performance and recovery are not established by Linux testing. No credentials are requested. Publishing is disabled in the wrapper environment; the pilot review console has no upload route. The localhost boundary does not authenticate against hostile local processes.

## Pilot

Selected Technology domain, English first, because a small reproducible hash experiment does not require licensed sports footage or GPU. The original 3-scene short explains SHA-256; sources checked for the hashing method: NIST Secure Hash Standard abstract (https://www.nist.gov/publications/secure-hash-standard), Python hashlib API documentation (https://docs.python.org/3/library/hashlib.html). Local experiment changes one character and records the full digests. The source declarations support the general method; they do not independently verify our experiment. The exact input/result JSON accompanies the demonstration. A matching hash alone is not proof of origin. No third-party footage/music is used. eSpeak synthetic English is a placeholder, not an approved professional voice; the whole draft remains synthetic and blocked regardless of self-attestations.

CLI (from repository root, create the private parent first):

```
python -m tools.pilot_pipeline example --output /private/example
python -m tools.pilot_pipeline build --plan /private/example/plan.json --assets /private/example/assets --output /private/run
python -m tools.domain_review_web --db /private/run/reviews.sqlite --catalog /private/run/catalog.json --port 8765
```

The example generator requires installed eSpeak or eSpeak NG; the supplied example inputs avoid that dependency on Windows. Custom owner plan/WAVs can use build directly. The build stages only declared WAV bytes after checking pinned hashes and PCM bounds, creates a fresh output directory, renders and audits, generates a review packet and empty template, registers the private queue and validates console startup configuration. A failed build leaves an explicit INCOMPLETE marker. No publication authority, automatic translation, word-level alignment, independent factual verification or rights certification. The pilot run receipt measures elapsed render+audit+queue time on the executing host, not owner PC performance.

## Exit criteria — must be evidenced, not guessed

- Actual Windows install and offline/pinned input render, browser playback and recovery drill; private logs.
- Real licensed English and Hindi narration with native-speaker listening and pronunciation review, fresh alignment and technical audit.
- Improved hook, differentiated graphics, readable captions and original source-backed editorial review; all actual checks reviewed, zero synthetic demo approval.
- Separate supervised PRIVATE upload via existing M3.2 gate on owner-authorized channel only; this pilot is not an eligible export. Verify metadata and Analytics with owner credentials; no public publish by default.
- Measure manual time, CPU time, revisions, costs, and only after separately approved publication, real audience performance. Freeze expansion into 12 domains until the one-channel workflow passes.
