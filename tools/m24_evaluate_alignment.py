#!/usr/bin/env python3
"""Offline, metadata-only word alignment timing evaluation.

A private corpus has human-reference and independently computed CTC candidate
word intervals. The tool DOES NOT generate references or infer a model.

Example:
  python tools/m24_evaluate_alignment.py --input C:/Private/corpus.json \
      --output C:/Private/new-timing-report.json

Store input/report OUTSIDE the public repo. Reports are never overwritten.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.m24_benchmark import evaluate_alignment_corpus


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    root=Path(__file__).resolve().parent.parent
    out=args.output.resolve()
    if args.input.resolve().is_relative_to(root):
        p.error('Keep private reference transcripts OUTSIDE the public source tree')
    if out.is_relative_to(root) or out.exists() or out == args.input.resolve():
        p.error('Use a NEW private report path outside the source repository')
    if args.input.stat().st_size>4*1024*1024:
        p.error('Benchmark input too large')
    report=evaluate_alignment_corpus(json.loads(args.input.read_text(encoding='utf8')))
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf8') as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
        f.write('\n')
    print(f"M2.4 timing benchmark: {report['status']} (owner review still required)")
    print('Saved private diagnostic:',out)


if __name__=='__main__':main()
