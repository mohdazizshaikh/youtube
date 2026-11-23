#!/usr/bin/env python3
"""Read-only offline voice rights/hash/audio QA preflight.

Example:
  python tools/m24_voice_preflight.py --profile voice.json --locale hi-IN \
      --sample narration.wav --report local_voice_qa.json

Voice manifest fields: backend="piper", locale="hi-IN", model_file,
sha256, rights_attested=true, license_reference, cloned_voice (optional),
speaker_consent (required for cloned_voice). Nothing is downloaded.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.m24_audio import validate_voice_profile, wav_audio_qa, SUPPORTED_LOCALES


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--locale', choices=sorted(SUPPORTED_LOCALES), required=True)
    parser.add_argument('--sample', type=Path)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    profile = json.loads(args.profile.read_text(encoding='utf8'))
    result = validate_voice_profile(profile, args.locale)
    if args.sample:
        result['sample_audio'] = wav_audio_qa(args.sample)
        result['sample_listening_required'] = True
    args.report.parent.mkdir(parents=True, exist_ok=True)
    if args.report.resolve() in {args.profile.resolve(), args.sample.resolve() if args.sample else None}:
        parser.error('Do not overwrite source manifest or audio')
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print('Local model verified; human naturalness and licensing review still required:', args.report)


if __name__ == '__main__':
    main()
