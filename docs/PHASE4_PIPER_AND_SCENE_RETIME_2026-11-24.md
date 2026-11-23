# ViralOS Phase 4 — Offline voice synthesis and localized scene retiming

**Scope:** newly implemented, *operator-triggered* M2.4/Piper narration drafts and M2.5 owner-cued scene timing. This is an engineering slice, not full M2.4/M2.5 acceptance or general auto-dubbing.

## Offline Piper engine integration

`app/m24_piper_runtime.py` verifies the file hashes of **three separately identified owner-local assets**: Piper executable, voice `.onnx`, and matching JSON configuration. It also requires a locale match, an identified licence reference and explicit owner commercial-use attestation; voice cloning additionally requires consent. The executable itself is owner-supplied/audited, and the code does **not** provide a network sandbox for third-party executables. In particular, a hash + owner attestation is not an independent copyright/licence check.

One user-authored text segment (up to 650 characters and 150 words) is handed to the local executable using a subprocess argument array, **without shell invocation**. Timeout, output size, path and audio checks are enforced; FFmpeg converts resulting WAV to 16kHz mono PCM16, and the audio QA module rejects severe silence/clipping/level issues. Existing output files cannot be overwritten. The returned JSON records the text, executable/model/config and output audio SHA-256 hashes without storing the full narration text. It always reports `DRAFT_SYNTHESIZED_OWNER_LISTENING_REQUIRED`.

No voice is bundled, no model auto-download or cloud speech API is invoked by ViralOS. External Piper binary behavior cannot be guaranteed network-free; owners should obtain trusted binaries and use an OS firewall/network isolation when strict offline operation is required.

### Example operator-only run

Prepare an owner-private JSON file **outside the Git repo**:

```json
{
  "backend": "piper",
  "locale": "en-US",
  "model_file": "C:/Models/english.onnx",
  "sha256": "<64 lowercase hex characters of model bytes>",
  "config_file": "C:/Models/english.onnx.json",
  "config_sha256": "<64 lowercase hex characters of config bytes>",
  "piper_binary_sha256": "<64 lowercase hex characters of installed Piper executable>",
  "rights_attested": true,
  "commercial_use_allowed_per_owner": true,
  "license_reference": "Owner-reviewed official voice model licence and terms, with date",
  "cloned_voice": false
}
```

```powershell
python tools/m24_synthesize_piper.py `
  --profile C:\Private\voice-profile.json `
  --binary C:\Tools\piper\piper.exe `
  --locale en-US `
  --text-file C:\Private\short-original-script.txt `
  --output-wav C:\Private\narration-draft.wav `
  --report C:\Private\narration-draft.report.json
```

For `hi-IN`, supply an actual licensed Hindi voice model with `language.code=hi_IN` and native Devanagari text. Do **not** assume an English voice can speak Hindi professionally. Listen to every name, date, number, loanword and emotional transition. Use the earlier CTC local-alignment workflow and independently annotated word timings for subtitle acceptance. None of these sample paths or hashes are actual downloadable voice assets.

## Scene-by-scene human-timed localized previews

`app/m25_dub_retime.py` rescales original shot lengths and in-shot motion-overlay timings from **owner-heard cumulative scene boundaries** (milliseconds). Unlike a proportional text-length guess, the final boundary must match the actual measured voice WAV duration (within 250ms). It does not adjust caption word timings or speech rate. Captions crossing a new scene boundary are rejected for owner re-timing; impossible 1.2–12s per-shot or 90s-total timelines fail closed. Huge shot-duration stretch requires manual reauthoring.

The existing route
`POST /api/projects/{project_id}/m25/localizations/{variant_id}/studio-preview`
now optionally accepts `scene_end_ms_json` (e.g. `[1600,2800]`) and `owner_verified_scene_boundaries=true` as **multipart form fields** alongside the existing approved plan and owner WAV. It returns `scene_retiming` provenance, while keeping the render marked **watermarked technical preview — not publish eligible**.

All content, captions and on-screen text must match the owner-reviewed localized script. Providing scene boundaries never substitutes for translation/factual/visual or professional audio review, nor does it change the private upload release gate.

## Evidence/limits

- Real FFmpeg tests exercise owner-cued timing with a **synthetic tone** WAV; the Piper CLI integration uses a synthetic fake executable/voice. This is deterministic software contract coverage, **not professional voice inference proof**.
- The owner still needs legal/licence assessment, working native Hindi/English Piper models, real CPU performance results, M2.4 word-alignment acceptance, native-speaker listening, and approval of two production-quality original demo videos.
- Actual machine privacy and network isolation, live YouTube credentials, owner-authorized PRIVATE upload and Analytics remain untested in this environment.
