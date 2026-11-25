# Phase 15B — offline narration preparation

Previous Phase 14C/15 verified at commit `5d8878dde81191e53123b3268c093efe6c14f7d4`, CI run 45640671172: Linux 486 passed, 749 hashes; Windows 374 passed, 46 skipped, PowerShell syntax passed. Hosted Windows is not owner hardware. This increment is a candidate pending its own CI.

Three opt-in commands operate on owner-local private files and trusted SHA-256 pins. No external services, model downloads, speech recognition, synthesis or permission to publish.

- Gain-only master: 16 kHz mono PCM16, 0.5–120 s; RMS target -26 to -16 dBFS, sample peak ceiling -6 to -1 dBFS, gain bounded -12 to +6 dB. Refuses existing or resulting technical flags. Exact frame count preserved; no trim, speed, EQ, denoise, compression, LUFS or true-peak measurement. Writes a new WAV only, never overwrites.
- Pronunciation glossary: locale-specific owner declarations, strict IDs, NFC/casefold Unicode token-sequence coverage and missing/unreviewed hint flags. Matches across punctuation and whitespace. Not phonetic validation, does not substitute terms or verify speech. Report excludes raw text and spoken hints.
- Bilingual scene timing: 2–8 ordered scene pairs, exact pinned WAV bytes, 25 fps common timeline using the longer narration rounded up to a video frame. Short <=60 s; long <=120 s. Reports per-language padding samples, reuse/quality/duration flags. No audio or video generated; no word-level alignment or translation proof.

```
python -m tools.narration_prepare master --audio /private/input.wav --audio-sha256 TRUSTED_PIN --output /private/master.wav
python -m tools.narration_prepare pronunciation --script /private/script.txt --script-sha256 TRUSTED_SCRIPT_PIN --glossary /private/glossary.json --glossary-sha256 TRUSTED_GLOSSARY_PIN --locale hi-IN
python -m tools.narration_prepare timing --root /private/tracks --request /private/timing.json --request-sha256 TRUSTED_REQUEST_PIN
```

Glossary JSON: schema VIRALOS_PRONUNCIATION_GLOSSARY_V1, locale, entries array of objects with id, term, spoken_hint, required (boolean), owner_reviewed (boolean). Owner declaration is not independently authenticated.

Timing JSON: schema VIRALOS_BILINGUAL_SCENE_REQUEST_V1, format SHORT or LONG, scenes array; each scene has integer scene (1-based), hindi and english objects with locale, file (safe leaf WAV name), sha256. Hindi hi-IN; English en-IN or en-US. Example fixture in regression tests.

Keep raw private files and reports outside Git. Record trusted pins independently. Operate on a quiescent owner-controlled directory; not hardened against a hostile concurrent local writer. WAV gain processing uses bounded memory (120 s). A successful command is not professional audio acceptance. The timing proposal is intentionally not wired into automatic rendering; future integration requires reviewed visual pacing and captions, actual voices and verified alignment. No publication eligibility is created.
