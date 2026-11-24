"""Audit existing local domain draft against its original assets and pinned manifest."""
import argparse
import json
from pathlib import Path
from app.domain_draft_audit import audit


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--draft',type=Path,required=True)
    p.add_argument('--assets',type=Path,required=True)
    p.add_argument('--manifest-sha256',required=True)
    p.add_argument('--report',type=Path,required=True)
    a=p.parse_args()
    report=audit(a.draft,a.assets,a.manifest_sha256)
    with a.report.open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')

if __name__=='__main__':main()
