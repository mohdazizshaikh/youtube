# Phase 14J — owner acceptance evidence checklist (2026-11-25)

This checklist is a preparation handoff, not an acceptance certificate. No field is pre-approved. Use a private owner-controlled working directory outside the Git checkout. Never submit credentials, recordings, license documents or reviewer notes to the repository. Keep Phase 13 and Phase 14 review environments separate. Synthetic videos remain review-only, even if every technical check passes.

| Gate | Required evidence | Initial status |
|---|---|---|
| Trusted source | Exact commit, package verifier output, successful CI for that commit | Pending owner verification |
| Local setup | Physical Windows version, Python/FFmpeg versions, installed dependency checks, RAQM/Devanagari font availability | Pending |
| English speech | Eight exact chapter recordings or approved local TTS outputs, verified WAV hashes, private rights/listening declarations, acoustic segmentation | Pending owner assets |
| Hindi speech | 24 exact segment recordings or approved local TTS outputs, WAV hashes, private rights/listening declarations | Pending owner assets |
| Real timing | Independently annotated reference and actual candidate model output, same pinned scripts/WAVs, representative bilingual benchmark (median <=80ms, p95 <=200ms) | Pending |
| Film assembly | Fresh renders from real narration, exact frame/stream checks, full decode, loudness gate, independent listening | Pending |
| Editorial | Native-language reviewers verify factual statements, sources, script completeness, pace, visual readability, genuine word timings, rights and truthful packaging; time-coded notes resolved | Pending |
| Browser | Real owner browser playback, audio, chapter seeking, caption visibility, note submission and restart persistence | Pending |
| Recovery | Private backup and restore to a new workspace; verified hashes, revision preservation and no overwrite of live data | Pending |
| Hardware | Physical owner PC CPU/RAM/disk and measured elapsed build/review time, errors and resource peaks | Pending |
| Account | Separate explicit owner authorization; existing M3.2 private-upload gate and private-only test, no public publish | Pending |
| Historic recovery | Owner-held source backup for 13–20 November | Pending |

## Reproduction order

1. Review the latest branch and manifest with `python tools/verify_package.py`; follow [Phase 13 Windows installation](PHASE13_DEPLOYMENT_AND_PILOT_2026-11-24.md) without bypassing local execution policy. Record actual results rather than a cloud CI substitute.
2. Create an English owner request using `python -m tools.phase14_bilingual english-request --plan tools/phase14_film_plan.json --output <new-private-folder>`. Review the scripts, record eight mono PCM16 48kHz WAVs, each 1–90 seconds, and fill actual hashes in a new manifest. Run `python -m tools.phase14_bilingual english-intake --plan tools/phase14_film_plan.json --manifest <private-manifest> --assets <private-assets>`. This verifies declared intake only, not speech accuracy, voice licensing or final render.
3. Use the Phase 14I Hindi request/prepare contract for 24 WAVs. New audio requires fresh durations and captions; never apply fixture timing to owner recordings. The Phase 14J renderer intentionally accepts synthetic Hindi intake only. Owner-speech render and real alignment integration are separate pending engineering work.
4. Benchmark actual English and Hindi candidate alignment against independent annotations using Phase 14H benchmark; keep model and rights references private. Require native listening and full watch-through. The 28-word synthetic arithmetic fixture is not evidence of acoustic alignment.
5. Inspect the synthetic English/Hindi draft films and metadata for revisions, not approval. Existing Phase 14H English review workspace has API-tested note persistence but browser acceptance is open. Hindi versioned console integration is still pending. Do not pass Hindi receipts off as English/legacy schemas.
6. After real media and editorial acceptance, use only the original, separately authorized private-account workflow. This checklist grants no upload or publication rights.

## Evidence to retain locally

Record date, commit and input/output SHA-256, hardware and dependency versions, exact commands, exit codes and log files, reviewer role and independently reviewed artifact hash, time-coded issues and resolution evidence. Keep all fields explicitly pending unless evidence exists. Do not share personal voice or account data in public issues. If a gate fails, preserve the failed output and logs; rebuild in a new private directory rather than modifying an accepted artifact. 
