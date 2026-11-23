#!/usr/bin/env python3
"""Owner-approved, model-hash-verified local Piper narration draft.

Use --profile for a local JSON with: backend="piper", locale="en-US" or
"en-IN" or "hi-IN", model_file, sha256, config_file, config_sha256,
piper_binary_sha256, rights_attested=true, license_reference,
commercial_use_allowed_per_owner=true. Cloned voices require speaker_consent.

This CLI uses no model downloads and never publishes. The owner must review
speaker rights, pronunciation, timing and naturalness. Report stores hashes
only, not the narration text. Never commit models or consent files to Git.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.m24_audio import SUPPORTED_LOCALES
from app.m24_piper_runtime import synthesize_piper_draft


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True,type=Path)
    parser.add_argument('--binary',required=True,type=Path)
    parser.add_argument('--locale',required=True,choices=sorted(SUPPORTED_LOCALES))
    parser.add_argument('--text-file',required=True,type=Path)
    parser.add_argument('--output-wav',required=True,type=Path)
    parser.add_argument('--report',required=True,type=Path)
    args=parser.parse_args(argv)
    targets=[args.profile.resolve(),args.binary.resolve(),args.text_file.resolve(),args.output_wav.resolve(),args.report.resolve()]
    if len(set(targets)) != len(targets):
        parser.error('Source, executable, output WAV and report paths must all differ')
    if args.text_file.stat().st_size > 4096:
        parser.error('Narration text too large for short-segment CPU synthesis')
    profile=json.loads(args.profile.read_text(encoding='utf-8'))
    text=args.text_file.read_text(encoding='utf-8')
    result=synthesize_piper_draft(profile,args.locale,args.binary,text,args.output_wav)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    with args.report.open('x',encoding='utf-8') as handle:
        json.dump(result,handle,indent=2,ensure_ascii=False)
    print('Synthesized draft; human listening and rights acceptance required: '+str(args.report))


if __name__=='__main__':
    main()
