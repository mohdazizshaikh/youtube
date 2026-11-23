#!/usr/bin/env python3
"""Owner-private, offline listening QA for actual WAV produced by m24_synthesize_piper.py.

Example:
 python tools/m24_review_voice.py --draft-report reports/narration.json \
  --wav reports/narration.wav --reviews reports/two-native-reviewers.json \
  --output reports/listening-verification.json

Only reviewer SHA-256 references are kept in output; do not publish the input
review notes, contracts, consent documents, or models to GitHub. Human claims
cannot be authenticated by this tool; no auto-upload approval is granted.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.m24_voice_acceptance import evaluate_voice_review


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('draft-report','wav','reviews','output'):
        p.add_argument('--'+name, type=Path, required=True)
    args=p.parse_args(argv)
    paths=[args.draft_report,args.wav,args.reviews,args.output]
    if len({x.resolve() for x in paths}) != 4:
        p.error('All input and output paths must differ')
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        p.error('Report must be new and in an existing local directory; no overwrite allowed')
    for inp in (args.draft_report,args.reviews):
        if inp.is_symlink() or not inp.is_file() or inp.stat().st_size > 100*1024:
            p.error('JSON input must be a bounded non-symlink local file')
    draft=json.loads(args.draft_report.read_text('utf8'))
    reviews=json.loads(args.reviews.read_text('utf8'))
    result=evaluate_voice_review(draft,args.wav,reviews)
    with args.output.open('x',encoding='utf8') as handle:
        json.dump(result,handle,ensure_ascii=False,indent=2)
        handle.write('\n')
    print(json.dumps({'status':result['status'],'reviewer_count':result['reviewer_count'],
                      'blockers':result['blockers'], 'auto_publish':False}))
    return 0 if not result['blockers'] else 2

if __name__=='__main__':raise SystemExit(main())
