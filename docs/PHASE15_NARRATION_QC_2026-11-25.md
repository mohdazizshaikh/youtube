# Phase 15 — offline narration diagnostics and Phase 14C stabilization

Phase 14B CI run 45579392913: Linux 414 passed, 744 hashes verified; Windows logs show 302 passed, 45 skipped, one FFmpeg-dependent test failed, then PowerShell parser failed. The Windows step was falsely reported successful because compileall masked pytest's exit. Fix candidate: reconstruct the damaged launcher tail, explicitly propagate pytest exit, mark the actual audio integration test skipped only when required media tools are absent (Linux still executes it), print parser errors. No assertion is weakened on hosts with FFmpeg.

Phase 15 adds stdlib-only diagnostics for locally supplied hash-pinned 16 kHz mono PCM16 WAV and UTF-8 script. Reports contain hashes, counts and metrics rather than raw script or private path. No network, speech model, download, synthesis or alignment. Technical metrics: peak/RMS dBFS, clip fraction, near-zero fraction, 20 ms quiet windows, lead/tail/longest quiet interval, DC offset and crest factor. Declared-text WPM and Unicode script mix are heuristic review flags, not ASR or language identification. Hindi/English pair compares duration and rejects identical PCM or script hashes. Distinct hashes do not prove distinct speech or translation.

Single example (record trusted pins separately):
```
python -m tools.narration_qc single --audio /private/hi.wav --script /private/hi.txt --locale hi-IN --audio-sha256 TRUSTED_AUDIO_PIN --script-sha256 TRUSTED_SCRIPT_PIN
```

Pair request JSON fields: schema=VIRALOS_BILINGUAL_QC_REQUEST_V1, hindi and english objects each with locale, audio, script, audio_sha256, script_sha256. Use leaf filenames only; Hindi locale hi-IN and English en-IN or en-US. Store request and inputs outside repo in owner-controlled local folder; record request SHA-256 independently.
```
python -m tools.narration_qc pair --root /private/input --request /private/request.json --request-sha256 TRUSTED_REQUEST_PIN
```

CLI stdout is JSON; redirect to a new private file if desired. Exit 0 means diagnostics executed, not quality acceptance. Any review flags require owner listening. Limits: 0.5–120 seconds, maximum bounded input bytes, no professional voice model or actual reference speech evaluated. No publication approval, pronunciation correctness or naturalness certification. Quiescent trusted local input required; no hostile concurrent writer guarantee. New tests and CI pending at authoring.

Next: owner-selected licensed voice models, real Hindi/English sample generation, pronunciation review, genuine CTC timing and pilot integration. Do not call the technical QC output an acceptance receipt.
