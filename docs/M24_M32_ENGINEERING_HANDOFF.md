# ViralOS M2.4 + M3.2 Engineering Handoff (2026-11-23)

**Scope:** Offline Hindi/English voice alignment, owner-review promotion, and supervised PRIVATE YouTube read-only acceptance. No old account was contacted. The original 12 November app/migrations/tests remain in place.

## M2.4 — what is code-complete vs not

**Implemented and unit/integration tested:**

- `app/m24_audio.py`: bounded CTC Viterbi path (acoustic model *emissions*, not heuristics), repeated token/blank handling, exact transcript-to-token grouping with rejection of unknown tokens, Unicode Hindi/English text, timestamp confidence calculations, PCM16 voice level/clipping diagnostics, local Piper model SHA and rights/consent preflight.
- `tools/m24_align_local.py`: optional local Hugging Face `AutoModelForCTC` + `AutoProcessor` with `local_files_only=True`, HF offline environment flags, `trust_remote_code=False`; reads user-provided 16 kHz mono WAV and reviewed transcript. Only acoustic logits from an existing local CTC model become timestamp evidence. Output is `DRAFT_OWNER_REVIEW_REQUIRED`. Does **not** download or bundle a model.
- `tools/m24_voice_preflight.py`: licensed model file/locale/hash checks and optional listening sample diagnostics. No claims about voice naturalness.
- `sql/009_m24_alignment.sql` and `app/m24_routes.py`: per-project/voice/plan/script-bound alignment drafts; explicit owner full-listening, spelling/timing/numbers approval, then safe promotion to existing M2.2 VTT word-timing records. Repeated or stale imports fail. Original user rights and source review still required.
- Existing M2.1 per-segment owner-supplied or opt-in Piper narration, locale-owned script variants, original sports diagrams and locally timed captions remain supported.

**External untested:** Running a real, language-compatible Hindi + English locally installed acoustic model on the owner's CPU; installed professional licensed Piper voice models; complete native multi-locale, translation, pronunciation and emotional direction; owner listening/visual review and clock speed on i7 CPU. A passed synthetic alignment test is **not** proof of an acoustic model or production-quality dubbing.

### Workflow

1. Owner records or synthesizes narration with permission and inspects the PCM16 WAV; match the **exact script** to the spoken words.
2. Place a compatible **already downloaded and licensed** CTC model/processor in a local path. Set no network-based model ID or auto-download. For example:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install torch transformers
   .\.venv\Scripts\python.exe tools\m24_align_local.py --wav C:\Local\voice.wav --transcript C:\Local\script.txt --model-dir C:\Models\approved-hindi-ctc --locale hi-IN --output C:\Local\words_draft.json
   ```

3. Listen and review every word and timestamp. Use `GET /api/m24/capabilities` to see limitations. The draft can be submitted to `POST /api/projects/{project_id}/m24/plans/{plan_id}/alignment-drafts` using exactly `locale`, `voice_audio_sha256`, `model_directory_name`, `method`, `status`, `words` (omit other CLI report fields). Voice SHA must match the M2.1 immutable plan voice file; transcriptions must exactly match M2.1 plan captions, including every word in the required scene window.
4. Once correct, explicitly call `POST /api/projects/{project_id}/m24/alignment-drafts/{draft_id}/owner-review` with all three true booleans plus reviewer identity. This imports to existing M2.2 word VTT provenance `EXTERNAL_ALIGNER_OWNER_REVIEWED` and **does not make a video publish-ready**.
5. Separately check on-screen Devanagari typography, properly localized graphics/title, source claims, licensed visuals/music, professional narration, human render review and next steps. If transcript does not fit or voice/plan changes, make a new project/plan; no silent overwrite.

**Key caveats:** Only short scenes up to 150 words/480 CTC tokens/4000 emission frames are accepted. Tokenizer must be prefix-stable and support the script vocabulary; not all Hindi tokenizers or acoustic models qualify. Forced alignment can still assign wrong speech an apparently plausible timestamp; independent owner listening is mandatory.

## M3.2 — private-owned-channel acceptance

- `app/m32_acceptance.py` verifies remote video ID, authorized channel ID, privacy **private**, title, description, tags, kids designation and synthetic media status where returned. Negative tests cover publicity, wrong ownership, metadata mutation and missing disclosure. IDs are hashed in shareable evidence.
- `tools/m32_private_acceptance.py` is an optional *read-only* owner-executed network check, after an existing separately authorized M3 private-upload intent. Requires local `VIRALOS_ENABLE_M32_READONLY_CHECK=1`, exact owner-selected intent and video ID, and explicit `I_AUTHORIZE_READONLY_CHECK`; uses OS-keyring OAuth, videos.list and optional YouTube Analytics daily report. No create/update/delete/visibility API calls.
- Failed `REMOTE_UNKNOWN` upload remains quarantined: verify in YouTube Studio, manually reconcile, never blind retry. The script does not automatically flip the intent's state and does not accept the release on the owner's behalf.
- No YouTube OAuth, channel identity, private upload or Analytics was performed inside the development environment; the live acceptance gate is still **BLOCKED on authorized owner credentials, API quota and explicit owner action**.

**Example owner-only read verification, after a private upload is independently completed:**

```powershell
$env:VIRALOS_ENABLE_M32_READONLY_CHECK="1"
.\.venv\Scripts\python.exe tools\m32_private_acceptance.py --intent-id YOUR_LOCAL_INTENT_ID --video-id YOUR_11_CHAR_VIDEO_ID --confirm-readonly-network I_AUTHORIZE_READONLY_CHECK --output C:\Private\viral_m32_audit.json
```

Optional `--analytics-start 2026-11-20 --analytics-end 2026-11-22` needs a *separate* authorized read-only Analytics credential. Private uploads might show no usable metrics yet. No revenue is fabricated.

## Windows M4 preflight

Run `powershell -ExecutionPolicy Bypass -File .\tools\windows_acceptance.ps1 -ReportPath C:\Private\viral_win_preflight.json` on the **actual owner Windows machine**. It reports CPU, RAM, Windows version, local Python 3.12, FFmpeg/FFprobe and Hindi fonts. It does not claim performance acceptance; after that, run a real preview/final render, playback with owner ears/eyes, DB backup/restore, restart-state persistence and M3 private review under actual hardware conditions. All reports remain local, not in Git.

## Safe priorities after this increment

1. Obtain genuine *authorized* local backups of 13–20 November work (do not access suspended GitHub account); reconcile by content hash, migrations, provenance, tests and owner approval.
2. Run both licensed local Hindi/English CTC and Piper models and time real CPU render/audio quality. Refine multilingual typography, pronunciation dictionary and music/SFX rights.
3. Run one owner-supervised YouTube private upload and read-only verification including account identity and analytics; preserve an audit locally without credentials; handle remote-unknown manually.
4. Execute owner Windows acceptance and disaster recovery tests; resolve any environment-specific breakage.
5. Independently review actual sources, rights and creative output with domain-specific human editors. Existing 12-domain profiles and 144 engine registrations remain designs, not 144 working specialist implementations.
6. Benchmark real domain directors and original videos before adding opt-in local GPU compute; no SaaS or public autopublishing pivot.
