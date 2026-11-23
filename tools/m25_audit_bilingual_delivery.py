#!/usr/bin/env python3
"""Offline English+Hindi original-video technical artifact audit.

Pass an owner-created JSON manifest matching docs/PHASE5_OWNER_AUDIO_BILINGUAL.md
and a private local evidence root (outside Git). All files are SHA-256 checked,
including the M2.4 native-listener reports, before an audit result is created.
No model, YouTube account, proprietary media or network access is used.
"""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.m25_bilingual_delivery import evaluate_bilingual_delivery


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True,type=Path)
    p.add_argument('--evidence-root',required=True,type=Path)
    p.add_argument('--report',required=True,type=Path)
    args=p.parse_args(argv)
    if args.manifest.is_symlink() or not args.manifest.is_file() or args.manifest.stat().st_size>100*1024:
        p.error('Manifest missing, symlinked, or too large')
    if args.report.exists() or args.report.is_symlink() or not args.report.parent.is_dir():
        p.error('Report must be a new file in an existing directory')
    payload=json.loads(args.manifest.read_text('utf8'))
    result=evaluate_bilingual_delivery(payload,args.evidence_root)
    with args.report.open('x',encoding='utf8') as f:
        json.dump(result,f,indent=2,ensure_ascii=False)
        f.write('\n')
    print(json.dumps({'status':result['status'],'blockers':result['blockers'],'publish_ready':False}))
    return 0 if not result['blockers'] else 2

if __name__=='__main__':raise SystemExit(main())
