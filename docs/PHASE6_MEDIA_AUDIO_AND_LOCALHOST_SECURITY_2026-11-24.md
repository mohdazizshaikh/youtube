# Phase 6 — Offline narration-in-render technical comparison and local HTTP isolation

This phase is designed to catch **two concrete engineering failures** without requiring remote access: (a) an otherwise apparently valid bilingual MP4 containing the wrong narration track; (b) a malicious website sending browser requests to a localhost-only ViralOS operator server. It does **not** close the voice, licensed assets, authorized YouTube, physical Windows or independent legal acceptance gates.

## M2.5 final rendered audio inspection

`app/m25_audio_conformance.py` decodes the **first MP4 audio track** offline with FFmpeg into bounded 16 kHz mono PCM16, inspects an owner-reviewed, SHA-256-locked 16 kHz mono PCM16 source WAV, and evaluates correlation across distributed 120-ms sample windows while searching up to 400 ms of audio offset. For positive technical conformance, the correlation must meet `0.65` and sampled coverage at least `0.80`. These values are **engineering heuristics**, not validated professional thresholds.

Integration: `app/m25_bilingual_delivery.py` calls this comparison for **both Hindi and English** inside the existing hash-bound artifact audit. Wrong audio blocks with `hi-IN:MP4_AUDIO_NOT_CONSISTENT_WITH_REVIEWED_NARRATION` or its English equivalent. An MP4 checksum alone does not validate actual spoken audio. The report includes the comparison score, offset and method, while `video_audio_contains_exact_reviewed_voice_proven` remains `false`.

### Hard limitations

- Strongly mixed background music, aggressive audio editing, time-stretching, clipping or long silence can cause false negatives. Review blocked packages rather than weakening the threshold automatically.
- A passing waveform correlation is **not** voice identity confirmation, proof of every spoken word, human-reviewed naturalness, copyright permission or subtitle/visual quality.
- The code checks the first audio stream only. A file with multiple audio streams or voice on other streams needs manual acceptance, not a guessed pass.
- No account, model, text, synthetic voice data, licensed song or remote media is downloaded. The tool uses local owner-supplied files. Generated recordings and their human reviews remain private outside Git.
- FFmpeg executes without a shell. The video file must already satisfy bounded size, path and SHA-256 checks from the bilingual audit.

Run `python tools/m25_audit_bilingual_delivery.py --manifest YOUR_PRIVATE_MANIFEST.json --evidence-root YOUR_PRIVATE_EVIDENCE_FOLDER --report NEW_PRIVATE_REPORT.json`. See the Phase 5 bilingual manifest guide. Reports must be outside the public repository and are always human-attestation-only, `publish_ready=false`.

## Local HTTP browser isolation

`app/local_http_guard.py` rejects requests before handlers run when the Host header is not `127.0.0.1`, `localhost` or `::1`; when a browser Origin does not match the precise host/scheme/port; or when the `Sec-Fetch-Site` header indicates `same-site` or `cross-site`. This blocks common DNS rebinding and cross-origin form attack paths. Server startup remains bound to `127.0.0.1` in `tools/start_windows.ps1`; do **not** publish port 8000, reverse-proxy to a public network, or forward it to a LAN interface.

Native CLI requests without a browser Origin still work, so this guard is **not authentication** against malware or a hostile local process. Tests use a `testserver` synthetic Host only when `PYTEST_CURRENT_TEST` is present or `VIRALOS_INTERNAL_TEST_CLIENT=1` is explicitly set for the bundled CLI smoke tool. Do not set that testing variable when running Uvicorn.

## Tests and reproducibility

Run `python -m pytest -q tests/test_m25_bilingual_delivery.py tests/test_local_http_guard.py` (FFmpeg required for real media tests); then `python -m pytest -q` and `python tools/verify_package.py` with an isolated synthetic database (`VIRALOS_DB` outside Git). Windows CI includes portable browser-guard checks; GitHub hosted Windows CI is not equivalent to the owner's actual i7/32 GB PC.

## Owner-side acceptance still needed

Owner must supply licensed Hindi and English voice/acoustic models, native-speaker listening reviews, annotated alignment benchmarks, two accepted finished bilingual films and their rights evidence; actual channel OAuth and supervised PRIVATE upload with Studio/Analytics; and a physical Windows install/backup/restore test. An offline archive from 13–20 November is still needed for complete historical recovery. Never access the suspended source account.
