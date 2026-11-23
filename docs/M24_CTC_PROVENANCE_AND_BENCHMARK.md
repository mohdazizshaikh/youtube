# M2.4 — Offline acoustic model provenance and word-alignment accuracy benchmark

**Checkpoint:** 24 November 2026, Phase 3. **Implementation is a local preflight and reference-based scoring tool, not an installed natural Hindi/English TTS model.** No model files, copyrighted speech recordings or OAuth credentials are committed. No internet calls are made by the tools.

## 1. Owner-provided acoustic model preflight

A valid local **CTC** model directory must contain `config.json`, tokenizer/processor assets and either `model.safetensors`, `pytorch_model.bin` or safetensors shards. The owner must create a separate manifest outside the model directory with SHA-256 for **every** file. All files and their hashes are verified before loading PyTorch/Transformers. Undeclared files, path traversal, symlinks, hash mismatches, absent rights attestations and wrong locale fail closed.

Example manifest **structure only** (replace fake values; not a verified license):

```json
{
  "schema": "VIRALOS_LOCAL_CTC_MODEL_V1",
  "model_id": "owner-approved-hi-ctc-001",
  "locale": "hi-IN",
  "license_reference": "Owner's actual local license and model provenance record",
  "owner_rights_review_attested": true,
  "commercial_use_allowed_per_owner": true,
  "files_sha256": {
    "config.json": "REPLACE_WITH_REAL_64_CHARACTER_SHA256",
    "preprocessor_config.json": "REPLACE_WITH_REAL_64_CHARACTER_SHA256",
    "tokenizer_config.json": "REPLACE_WITH_REAL_64_CHARACTER_SHA256",
    "model.safetensors": "REPLACE_WITH_REAL_64_CHARACTER_SHA256"
  }
}
```

This sample is intentionally invalid until real hashes/rights are supplied. The owner must add all real local files, including tokenizer assets. To verify hashes and ownership attestations **without** installing Torch or running speech inference, first run `python tools/m24_model_preflight.py --model-dir C:/Models/LicensedCTC --model-manifest C:/Private/licensed-ctc-manifest.json --locale hi-IN --output C:/Private/new-model-check.json`. A model that doesn't support the locale or lacks a usable CTC blank/pad token will still fail at inference. A hash is **not** a legal opinion or a voice-quality benchmark.

```powershell
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
python tools/m24_align_local.py --wav C:\Private\narration.wav `
  --transcript C:\Private\narration.txt `
  --model-dir C:\Models\LicensedCTC `
  --model-manifest C:\Private\licensed-ctc-manifest.json `
  --locale hi-IN --output C:\Private\alignment-draft.json
```

Transcript words/timings remain a **DRAFT** until per-word owner listening review and the existing M2.4/M2.2 import gate. Only use language-compatible models; no model will be downloaded or selected automatically.

## 2. Ground-truth timing benchmark

Create a private `VIRALOS_CTC_BENCHMARK_V1` JSON containing `locale`, a verified **model manifest SHA-256**, and individual samples (`sample_id`, a distinct `audio_sha256`, `duration_ms`, `human_reference`, `ctc_candidate`). A reference entry has `token`, `start_ms`, `end_ms`; candidate entries add `acoustic_score` in `[0,1]`. Every reference token must match the corresponding candidate token exactly (including Hindi matras and punctuation). Timestamps must be ordered, positive and inside the declared duration.

Example for **one synthetic sample only** (far too small for a benchmark):

```json
{
  "schema": "VIRALOS_CTC_BENCHMARK_V1",
  "locale": "hi-IN",
  "model_manifest_sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
  "samples": [{
    "sample_id": "synthetic-demo-001",
    "audio_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "duration_ms": 1200,
    "human_reference": [
      {"token": "नमस्ते", "start_ms": 50, "end_ms": 490},
      {"token": "दोस्तों", "start_ms": 550, "end_ms": 1100}
    ],
    "ctc_candidate": [
      {"token": "नमस्ते", "start_ms": 90, "end_ms": 510, "acoustic_score": 0.86},
      {"token": "दोस्तों", "start_ms": 570, "end_ms": 1130, "acoustic_score": 0.81}
    ]
  }]
}
```

Run:

```powershell
python tools/m24_evaluate_alignment.py --input C:\Private\ctc-benchmark-input.json `
  --output C:\Private\ctc-benchmark-results-NEW.json
```

The diagnostic compares absolute start/end errors. For *threshold review* require **at least 10 distinct recordings and 200 verified words**, with median boundary error <=100 ms and 95th percentile <=250 ms; this is an initial engineering target, **not a universal production speech-quality criterion**. Real native-speaker listening, model right-to-use, punctuation, pronunciations, Hindi/English dialect coverage and target i7/32GB inference speed still require external testing.

The evaluator deliberately does **not** read WAV bytes, authenticate human annotations, load the model, or invent transcripts. Its output uses aggregate numbers and SHA-256, and never marks the project publication approved. Owner's private WAVs, annotation files and outputs must remain outside public Git and must not contain secrets.

## 3. Acceptance still blocked without owner resources

- At least one legally usable, language-correct **local acoustic model** and reproducible benchmark inputs.
- Professional, commercially appropriate local voices with owner-reviewed provenance and listening tests in Hindi/English/Hinglish.
- Real word-alignment benchmark on physical Windows i7/32GB, using owner-reviewed reference timestamps.
- Scene re-timing/dubbing quality and final translated video watch-through (current M2.5 video remains technical preview only).

No step above implies automatic translation, voice cloning, YouTube publication or real-world acceptance.
