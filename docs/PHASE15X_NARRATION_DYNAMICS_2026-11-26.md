# Phase 15X — bounded narration dynamics mastering candidate

Phase 15S verified CI 45716301815: Linux 1503 passed/832 hashes, Windows 1369 passed/68 skipped. T Windows 1413 passed/68 skipped (50 warnings); U Windows 1453 passed/68 skipped (50 warnings); Linux pending at authoring. V/W pending. Phase 15X new CI pending.

## Operator workflow
Owner-local pinned clean mono 16 kHz PCM16 narration, 3–120 seconds. No trim, resampling, time stretch, ASR or phonetic correction. Source QC and FFmpeg loudnorm measurement mandatory. Compressor uses 20 ms block RMS, bounded 12 dB attenuation, attack/release smoothing, threshold -36..-10 dBFS and ratio 1.5..4. Re-measure compressed voice, apply bounded -12..+6 dB makeup gain toward -23..-14 LUFS target, then forward-window sample-peak limiter (2–10 ms lookahead, 30–300 ms release, max 12 dB attenuation). Instant downward gain and smoothed release; lookahead avoids shifting samples but is not a studio-grade brickwall true-peak limiter. Sample peak ceiling set 1 dB below requested -6..-1 dBTP; output FFmpeg measured true peak must meet actual ceiling or fail. Output target proximity is diagnostic, not guaranteed. Exact sample count, zero/sign preservation and source/output QC. No clipping correction, denoise, de-essing, EQ or professional listening certification.

Request fields: schema VIRALOS_NARRATION_DYNAMICS_REQUEST_V1, voice_sha256, threshold_dbfs, ratio, attack_ms integer 5–100, release_ms integer 50–500 (>= attack), target_lufs, ceiling_dbtp, lookahead_ms, limiter_release_ms. Pin exact request and original WAV bytes separately.
```
python -m tools.narration_dynamics build --voice PATH --request PATH --request-sha256 PIN --output NEW_PATH
python -m tools.narration_dynamics verify --voice PATH --request PATH --request-sha256 PIN --output PATH --dynamics-sha256 PIN
```
Output master.wav and dynamics.json. Exclusive output directory with incomplete marker; verify fresh deterministic processing and same-environment FFmpeg measurements, exact audio/receipt bytes. Preserve original source and request. No publishing, no automatic substitution into existing pilots, no voice license or professional quality claim. Real synthetic variable-amplitude tone integration test plus portable algorithm and request tests. Motion combination deferred until queued motion CI passes.
