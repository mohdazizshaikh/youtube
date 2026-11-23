#!/usr/bin/env python3
"""Verify owner-supplied CTC acoustic-model hashes/rights, WITHOUT loading a model.

Example:
  python tools/m24_model_preflight.py --model-dir C:/Models/OwnerCTC \
    --model-manifest C:/Private/ctc-model-manifest.json --locale hi-IN \
    --output C:/Private/new-model-preflight.json

No Hub, Torch, audio or network activity. A manifest attestation is not
independent license clearance or proof of usable professional voices.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.m24_provenance import inspect_ctc_model
from app.m24_audio import SUPPORTED_LOCALES


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-dir',required=True,type=Path)
    p.add_argument('--model-manifest',required=True,type=Path)
    p.add_argument('--locale',required=True,choices=sorted(SUPPORTED_LOCALES))
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args(argv)
    out=args.output.resolve();root=Path(__file__).resolve().parent.parent
    if out.exists() or out.is_relative_to(root) or out==args.model_manifest.resolve():
        p.error('Use a NEW private report path outside the public repo')
    result=inspect_ctc_model(args.model_dir,args.model_manifest,args.locale)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
        f.write('\n')
    print(result['status'],'| human speech-quality evaluation still pending')
    print('Private result:',out)

if __name__=='__main__':main()
