# Phase 14L — owner narration assembly and local voice runtime (2026-11-25)

Base ce9898a43fe834f12c6e8cf85308e856abac5c66; [Phase 14K CI run 45481721345](https://github.com/mohdazizshaikh/youtube/actions/runs/45481721345) initially in progress, later verified successful. Draft PR #7; main preserved at Phase 13.

## Executed workstreams

- New English owner-assembly input validation: exact pinned original plan and externally pinned retime receipt, 24 ordered shots, contiguous declared source sample and word boundaries per chapter, exact script text and individual PCM WAV hashes, frame and zero-padding calculations, whole assembled WAV byte-level PCM equality. It checks retime declarations and staged audio, not original chapter files, actual spoken content, rights or semantic cuts. No synthetic word timing reused; captions omitted.
- Actual 24-shot fixture render: eight original chapters, exact 932-word script coverage, 744 frames at 1920x1080/30fps, 24.8s video/audio, H.264/AAC, complete decode passed. Two parallel encoders, original flow/bit-grid/compare progressive boards and short shot fades. No continuous semantic animation. Sampled frame visually inspected. Explicit ARTIFICIAL PCM TEST / NO SPEECH / NO RELEASE footer (also faded at shot starts). Eight artificial 440Hz tone WAVs with fixture-only declarations; not owner recordings or professional content. Numeric audio gate failed (-22.11 LUFS/-18.01 dBTP, LRA 0); no mastering attempted on tones. Render+audit 10.39s on isolated Linux host, not owner hardware. Video SHA256 827e3077d081f1e8e86ea2f9cd801ecdad9f3dc5661c733bdacbd523f4a0966c; narration af22227c34945ac38178dfaade749d1d01311a4aaf7d2f47e296ddcdae1f65bf; retime receipt aee6cde9eefde65f5a9139f788b85c6b674b557628b9145293f12d52ba1aeb0b. Previous full English/Hindi synthetic review films unchanged.
- Local Piper adapter: explicit inspect/synthesize commands, externally pinned manifest, absolute local executable/model/config paths with SHA256 and size caps, declared private rights, supported locale and bounded config sample rate, script hash, subprocess timeout and no shell, output PCM validation and FFmpeg normalization to mono PCM16 48kHz; checks asset hashes again after invocation, marks human listening and alignment unverified, exclusive output/INCOMPLETE marker. No Piper executable/model available on host. Tests used deliberately non-executable/non-model bytes to validate hash/manifest contracts and prove script mismatch prevents invocation. No actual inference or normalization execution in this increment; CLI flag compatibility, native dependencies and model quality need actual testing. Use trusted owner-controlled binaries and paths; not a sandbox or enforced network isolation, hash pins alone do not prove trust or licensing. No network/model downloads performed by adapter.
- 16/16 new tests and 69/69 combined Phase 14I/J/K/L tests passed locally. Three source/test Git blobs matched local tested bytes. Personal Library copies of the three source/test files used for Git transfer. No private voice/media/rights data committed. Latest CI pending after manifest refresh. Full local checkout previously DNS-blocked; not re-tested here. No live account, production DB migration, owner hardware, browser playback or publishing action.

## Reproduction and owner handoff

Run from repository root on trusted Python/Pillow, FFmpeg and owner-controlled local storage. Fresh private directories, no overwrite, keep INCOMPLETE outputs. Do not commit private assets or license references. English owner WAV intake and reviewed-boundary retime are Phase 14J/K prerequisites.

    python -m tools.phase14_owner_assembly --plan tools/phase14_film_plan.json --folder <retimed-folder> --expected <receipt-sha256> --output <new-output> --fontpath <local-font.ttf>
    python -m tools.phase14_voice_runtime inspect --manifest <private-runtime.json> --expected <manifest-sha256>
    python -m tools.phase14_voice_runtime synthesize --manifest <private-runtime.json> --expected <manifest-sha256> --script <reviewed-script.txt> --script-sha <script-sha256> --output <new-private-voice-output>
    python -m pytest -q tests/test_phase14_owner_assembly.py tests/test_phase14_workspace.py tests/test_phase14_bilingual.py tests/test_phase14_localize.py

Use --fixture for artificial PCM tests only. For voice runtime, manifest schema VIRALOS_LOCAL_PIPER_V1, locale en-US/en-IN/hi-IN, rights_attested true and private rights_reference, executable/model/config objects each with absolute path and exact sha256. Example conceptual config: audio.sample_rate must be integer 8000–48000. Only select owner-trusted licensed local binaries and models, after verifying provenance, compatibility and dependencies. No automatic installation. Runtime receipt is not an owner intake acceptance: native listening and actual script/speech verification plus original rights declaration still needed; use Phase 14J/K contracts for recording intake and cuts. Run real independent alignment benchmark before caption generation. Do not reuse fixture cues. Master and fresh-audit actual owner film only after real audio and visual review. No direct release or queue registration in this new assembly.

## Consolidated priorities

| Priority | Gate | Status / next proof |
|---|---|---|
| P0 | CI/package | Phase 14K green; Phase 14L manifest refresh/latest CI pending |
| P0 | English real-narration reassembly | ENGINE_FIXTURE_TESTED; actual licensed owner audio and reviewed cuts absent; real full-length render pending |
| P0 | Hindi real-narration reassembly | Intake ready from Phase 14I; real-speech render path and true captions pending |
| P0 | Local natural voice runtime | PINNED_ADAPTER_CONTRACT_TESTED; actual executable/model, inference and native listening blocked |
| P0 | Real acoustic alignment | Benchmark ready from Phase 14H; real model inference and independent annotations pending |
| P0 | Genuine captions | Owner assembler omits unverified cues; actual word-timing integration pending |
| P0 | Visual quality | Fixture progressive boards/fades only; differentiated cinematic motion and full human readability pending |
| P0 | Audio | Prior full bilingual synthetic films passed numeric gates; artificial assembly fixture fails mastering gate, real narration mix pending |
| P1 | Bilingual review/recovery | Phase 14K API and isolated restore tested; actual browser, physical Windows restore and human revisions pending |
| P1 | Packaging/editorial | Drafts only; independent factual, native-language and rights review required |
| P1 | YouTube | BLOCKED_OWNER_AUTHORIZATION; no live upload/analytics |
| P2 | Resource optimization | Two encoders, 10.39s short artificial fixture; no owner full-length CPU/RAM benchmark |
| Recovery | 13–20 Nov source | BLOCKED_OWNER_BACKUP |
| Release | Merge | OPEN; latest CI, owner and editorial acceptance; main preserved |

Next: real licensed voice/model and independent annotations, actual bilingual runtime test and speech-to-film integration, real global captions, differentiated visual motion and perceptual review, owner Windows/browser/restore and separately authorized private-account acceptance. See [project status](PROJECT_STATUS.md) and [owner acceptance checklist](OWNER_ACCEPTANCE_2026-11-25_PHASE14J.md). No synthetic release, public publishing or 12-domain expansion.
