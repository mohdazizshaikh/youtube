#!/usr/bin/env python3
"""M2.4 opt-in, offline *real* acoustic forced alignment.

Requires a pre-installed local Hugging Face CTC acoustic model and processor
compatible with the given spoken language. No model is downloaded; no token or
network access is performed. Output is a DRAFT that must be listened to and
reviewed by the owner before importing to M2.2 word timing API.

Example (model files provided by owner):
  python tools/m24_align_local.py --wav narration.wav --transcript captions.txt \
    --model-dir C:/models/approved-hi-ctc --model-manifest C:/Private/ctc-model-manifest.json \
    --locale hi-IN --output C:/Private/draft.json
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import wave

# Make script runnable directly from repo root or tools/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.m24_audio import (ctc_viterbi, prefix_token_groups, split_words,
                           word_intervals, wav_audio_qa, SUPPORTED_LOCALES)
from app.m24_provenance import inspect_ctc_model


def align_local(wav: Path, transcript: str, model_dir: Path, locale: str, model_manifest: Path) -> dict:
    if locale not in SUPPORTED_LOCALES:
        raise ValueError('Supported locales: en-US, en-IN, hi-IN')
    if not model_dir.is_dir():
        raise ValueError('Local CTC model folder missing; network download not allowed')
    provenance = inspect_ctc_model(model_dir, model_manifest, locale)
    qa = wav_audio_qa(wav)
    if qa['technical_flags']:
        raise ValueError('Narration fails technical audio QA: ' + ', '.join(qa['technical_flags']))
    # Prevent implicit HF Hub calls even when a cached model reference is supplied.
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    try:
        import torch
        from transformers import AutoProcessor, AutoModelForCTC
    except ImportError as ex:
        raise RuntimeError('Install optional local CPU PyTorch and Transformers dependencies') from ex
    processor = AutoProcessor.from_pretrained(str(model_dir.resolve()), local_files_only=True,
                                              trust_remote_code=False)
    model = AutoModelForCTC.from_pretrained(str(model_dir.resolve()), local_files_only=True,
                                           trust_remote_code=False).to('cpu').eval()
    blank = model.config.pad_token_id
    if blank is None:
        blank = getattr(processor.tokenizer, 'pad_token_id', None)
    if blank is None:
        raise ValueError('CTC model needs a blank/pad token ID')
    words = split_words(transcript)
    targets, groups = prefix_token_groups(processor.tokenizer, words, blank)
    if getattr(processor.feature_extractor, 'sampling_rate', None) != 16000:
        raise ValueError('Local CTC acoustic model sample rate must be 16000 Hz')
    with wave.open(str(wav), 'rb') as audio:
        raw = audio.readframes(audio.getnframes())
    # PCM16 little endian is guaranteed by wav_audio_qa.
    import array
    import sys as _sys
    floats = array.array('h'); floats.frombytes(raw)
    if _sys.byteorder == 'big':
        floats.byteswap()
    audio_float = [float(s) / 32768 for s in floats]
    inputs = processor(audio_float, sampling_rate=16000, return_tensors='pt')
    with torch.no_grad():
        logits = model(inputs.input_values.to('cpu')).logits.squeeze(0)
        logp = logits.log_softmax(dim=-1)
    del model, inputs, audio_float
    # Materialize only the needed token columns: bounded CPU memory use.
    required = sorted(set([blank] + targets))
    if any(t >= logp.shape[-1] for t in required):
        raise ValueError('Tokenizer/model vocabulary mismatch')
    compact = logp[:, required].cpu().tolist()
    positions = {t: i for i, t in enumerate(required)}
    spans = ctc_viterbi(compact, [positions[t] for t in targets], positions[blank])
    result = word_intervals(words, groups, spans, qa['duration_ms'], len(compact))
    return {'m24_alignment_version': '0.1', 'status': 'DRAFT_OWNER_REVIEW_REQUIRED',
            'locale': locale, 'method': 'OFFLINE_CTC_VITERBI_FORCED_ALIGNMENT',
            'model_directory_name': model_dir.name,
            'model_manifest_sha256': provenance['manifest_sha256'],
            'model_id': provenance['model_id'],
            'voice_audio_sha256': qa['audio_sha256'],
            'acoustic_frames': len(compact), 'audio_qa': qa,
            'words': result, 'owner_reviewed': False,
            'warning': 'Forced alignment does not verify transcript accuracy, pronunciation, translation, facts or rights. '
                       'Listen to the audio and correct every word timestamp before importing it.'}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--wav', type=Path, required=True)
    ap.add_argument('--transcript', type=Path, required=True)
    ap.add_argument('--model-dir', type=Path, required=True)
    ap.add_argument('--model-manifest', type=Path, required=True,
                    help='Owner-provided local license/hash inventory outside the model directory')
    ap.add_argument('--locale', choices=sorted(SUPPORTED_LOCALES), required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(argv)
    transcript = args.transcript.read_text(encoding='utf-8')
    output = args.output.resolve()
    root = Path(__file__).resolve().parent.parent
    if output in (args.transcript.resolve(), args.wav.resolve(), args.model_manifest.resolve()) or output.is_relative_to(root) or output.exists():
        ap.error('Use a NEW output path outside the source repository and model evidence')
    result = align_local(args.wav, transcript, args.model_dir, args.locale, args.model_manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x',encoding='utf8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('Offline CTC word alignment DRAFT generated. Owner listening/review REQUIRED.')
    print('Output:', args.output, 'Words:', len(result['words']))


if __name__ == '__main__':
    main()
