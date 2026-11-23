#!/usr/bin/env python3
"""Offline post-upload owner Studio checklist bound to read-only OAuth evidence.

This never contacts Google. First run m32_private_acceptance.py on owner machine,
then manually inspect PRIVATE video and analytics in YouTube Studio, and supply
private operator checklist JSON. Final report stores no raw IDs, metrics or notes.
"""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.m32_owner_signoff import combine_readonly_studio_evidence


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--api-evidence',required=True,type=Path)
    p.add_argument('--owner-studio-checklist',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args(argv)
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        p.error('Evidence output must be new, in an existing local directory')
    files=(args.api_evidence,args.owner_studio_checklist)
    if args.output.resolve() in {x.resolve() for x in files}:
        p.error('Evidence input/output collision')
    for path in files:
        if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=256*1024:
            p.error('Local JSON evidence missing, oversized or symlinked')
    api=json.loads(args.api_evidence.read_text('utf8'))
    studio=json.loads(args.owner_studio_checklist.read_text('utf8'))
    audit=combine_readonly_studio_evidence(api,studio)
    with args.output.open('x',encoding='utf8') as f:
        json.dump(audit,f,ensure_ascii=False,indent=2)
        f.write('\n')
    print(json.dumps({'state':audit['state'],'blockers':audit['blockers'],
                      'automatic_publish':False}))
    return 0 if not audit['blockers'] else 2

if __name__=='__main__':raise SystemExit(main())
