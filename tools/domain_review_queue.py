"""Local owner-only review queue; use a database outside the public repository."""
import argparse
import json
from pathlib import Path
from app.domain_review_queue import initialize, register, submit, status


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['init','register','submit','status'])
    p.add_argument('--db',type=Path,required=True)
    p.add_argument('--draft',type=Path)
    p.add_argument('--assets',type=Path)
    p.add_argument('--manifest-sha256')
    p.add_argument('--expected-revision',type=int)
    p.add_argument('--review',type=Path)
    a=p.parse_args()
    if a.db.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        p.error('keep the private database outside the repository')
    if a.mode=='init':
        initialize(a.db); result={'initialized':True,'publication_eligible':False}
    elif a.mode=='status': result=status(a.db)
    else:
        if a.draft is None or a.assets is None or a.manifest_sha256 is None:
            p.error('draft, assets and manifest SHA-256 required')
        if any(a.db.resolve().is_relative_to(x.resolve()) for x in (a.draft,a.assets)):
            p.error('database must be outside audited inputs')
        if a.mode=='register':
            result=register(a.db,a.draft,a.assets,a.manifest_sha256)
        else:
            if a.review is None or a.expected_revision is None:
                p.error('review file and expected revision required')
            with a.review.open('rb') as f: raw=f.read(128001)
            if len(raw)>128000:p.error('review file too large')
            result=submit(a.db,a.draft,a.assets,a.manifest_sha256,a.expected_revision,json.loads(raw))
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
