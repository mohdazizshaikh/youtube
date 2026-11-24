"""Compose a local reviewed-source draft with owner-provided narration WAVs."""
import argparse
import json
from pathlib import Path
from app.domain_draft_video import DraftPlan, compose


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',required=True,type=Path)
    p.add_argument('--assets',required=True,type=Path)
    p.add_argument('--output-dir',required=True,type=Path)
    a=p.parse_args()
    plan=DraftPlan.model_validate_json(a.plan.read_text(encoding='utf8'))
    print(json.dumps(compose(plan,a.assets,a.output_dir),indent=2))

if __name__=='__main__':main()
