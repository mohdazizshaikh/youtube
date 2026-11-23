# ViralOS Phase 5 — Operator-only voice, bilingual deliverable, Studio evidence

**Date:** 2026-11-24  
**Repo:** `mohdazizshaikh/youtube`. The former suspended account must never be contacted.  
**All private evidence MUST stay outside the Git checkout** (voice model, voice recordings, prompts, original client secrets, OAuth tokens, Studio screenshots, rights contracts, reviewer identities and notes).

## Gate A — Actual local synthesized voice + two native-language listening attestations

1. Obtain a commercially permitted Hindi or English Piper model, matching config, executable and recorded permission/consent from an authorized source independently. No software here grants or certifies rights. Execute `tools/m24_synthesize_piper.py` with user-supplied paths/hashes to create a **draft WAV and JSON report**. No model or executable is automatically downloaded, and a third-party executable cannot be proven network-free by this adapter.
2. On the owner machine, listen through the entire draft; check script, number/name pronunciation, naturalness, intelligibility, artifact noise, timing, and voice rights. Obtain two genuinely distinct native-language human reviews for each target locale. Mark each checklist flag truthfully and record 1–5 scores plus private notes. The expected JSON structure is shown in `tests/test_m24_voice_acceptance.py`, whose examples are explicitly synthetic and must not be reused as human review evidence.
3. In an owner-only private folder, run:

   ```powershell
   py -3.12 tools/m24_review_voice.py --draft-report C:\Private\narration-draft.json --wav C:\Private\narration.wav --reviews C:\Private\two-reviewers.json --output C:\Private\review-receipt.json
   ```

   Output records verified WAV SHA-256, technical QA, per-reviewer hashes and reported flags; it **cannot verify a human actually listened** or that the license is genuine. A synthetic test review may pass software logic and is **not acceptance evidence**. The tool never enables public/private publishing.

## Gate B — Two original videos, one in Hindi and one in English

Provide a **private** manifest with exactly one `hi-IN` and one `en-US` variant, common source-script/evidence hashes and independently localized script (.txt), exact transcript SRT (.srt), narration (.wav), H.264 video with audio (.mp4), source/rights metadata (.json), and voice-review receipt (.json). Every artifact entry uses `{ "path": "relative/file.ext", "sha256": "64-lowercase-hex-digits" }` relative to an existing private evidence directory. Each locale requires a separate owner reviewer and five explicit review boolean flags.

The `voice_review.text_sha256` must match the **actual bytes** of that variant's script file. SRT cues must have consecutive numeric IDs starting at 1, exact `HH:MM:SS,mmm --> HH:MM:SS,mmm` clocks, no overlaps, nonempty text, transcript equal to script and no cue ending beyond actual video duration (250 ms rounding tolerance). Real video probing requires an installed FFprobe. These checks reject obvious production mismatches but **do not prove the video's audio matches the original WAV**, perceptual subtitle/graphic quality, independent source accuracy, originality or legal rights.

Run on the owner PC (local files only):

```powershell
py -3.12 tools/m25_audit_bilingual_delivery.py --manifest C:\Private\bilingual.json --evidence-root C:\Private\bilingual-files --report C:\Private\bilingual-audit.json
```

The no-overwrite output remains explicitly `publish_ready: false` even if technical checks and owner attestations pass. For full release acceptance, a human must watch both rendered videos end-to-end and independently verify source/rights, captions, typography and audio in intended playback clients.

## Gate C — Already uploaded, authorized YouTube PRIVATE video (read-only)

1. First, on the owner's machine with owner-approved OAuth configuration, perform the existing **supervised** PRIVATE upload procedure only after all M2.6 editor checks. Never upload a test video as public or unlisted and never share OAuth credentials.
2. Use `tools/m32_private_acceptance.py` to obtain the genuine read-only PRIVATE-status + channel/video metadata + Analytics observation report. For `REMOTE_UNKNOWN`, use the safe no-duplicate reconciliation procedure first.
3. Open YouTube Studio yourself and verify PRIVATE status, correct channel, video sound/metadata and any policy/copyright alerts. Record truthful private checklist booleans and descriptive owner notes; their schema is in `tests/test_m32_owner_signoff.py` (synthetic examples only). Then run:

   ```powershell
   py -3.12 tools/m32_signoff_studio.py --api-evidence C:\Private\read-only.json --owner-studio-checklist C:\Private\studio-review.json --output C:\Private\studio-evidence-receipt.json
   ```

This binds hashes to report bytes and checks a 30-day freshness window, private status, correct API flags and Analytics state. It **does not independently authenticate Google, Studio actions, reviewer identity, analytics values or upload rights** and never changes privacy or publishes. A passing synthetic fixture MUST NOT be submitted as real acceptance.

## Physical Windows i7 / 32 GB owner acceptance and recovery

Run `tools/run_windows_local_acceptance.ps1` in a private new report directory **outside the repo**, after manually installing Python 3.12, FFmpeg, suitable Hindi fonts and approved local voice models. Save hardware preflight, real CPU media playback, no-network synthetic backup/restore drill, source hash checks, owner controlled actual-data recovery test, locale reviewer receipts, rights audit and authorized Studio evidence separately. Cloud Windows CI is **not** this physical-machine test. Avoid storing private reports in public GitHub.

## Critical unresolved external dependencies

- Missing 13–20 November original source requires a user-held offline backup and `tools/reconcile_owner_backup.py`. Do not connect the suspended GitHub account.
- Native voice/acoustic models, commercial rights, CPU timing benchmarks and real Hindi/English listening have not been supplied/verified.
- Real owner OAuth, PRIVATE upload + Analytics and physical Windows target testing have not occurred here.
- No verified 24 production videos / 12 fully autonomous domain experts / GPU inference or authentic revenue metrics yet.
