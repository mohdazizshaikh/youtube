"""Create local editorial packets or evaluate a completed checklist. Never publishes."""
import argparse
import json
from pathlib import Path
from app.domain_draft_review import review_packet, template, evaluate


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['prepare','evaluate'])
    p.add_argument('--draft',type=Path,required=True)
    p.add_argument('--assets',type=Path,required=True)
    p.add_argument('--manifest-sha256',required=True)
    p.add_argument('--output',type=Path,required=True,help='New private file outside the draft directory and repository')
    p.add_argument('--review',type=Path)
    a=p.parse_args()
    if a.output.resolve().is_relative_to(a.draft.resolve()) or a.output.resolve().is_relative_to(a.assets.resolve()):
        p.error('output must be outside audited input directories')
    if a.mode=='prepare':
        packet=review_packet(a.draft,a.assets,a.manifest_sha256)
        result={'packet':packet,'review_template':template(packet)}
    else:
        if a.review is None:p.error('--review required')
        with a.review.open('rb') as f:raw=f.read(128001)
        if len(raw)>128000:p.error('review file too large')
        result=evaluate(a.draft,a.assets,a.manifest_sha256,json.loads(raw))
    with a.output.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    return 2 if a.mode=='evaluate' and not result['self_attested_editorial_checklist_complete'] else 0

if __name__=='__main__':raise SystemExit(main())
