#!/usr/bin/env python3
"""Supervised M3.2 RECONCILE, not reupload, a remotely uncertain PRIVATE video.

Requires the owner-connected upload OAuth and an *existing* remote 11-char video
ID, with an exact live `videos.list` match, human YouTube Studio review and an
explicit local opt-in. No upload, privacy change, delete or publishing endpoint
is called. This tool deliberately cannot locate unknown videos automatically.

Run only on the owner's computer, after checking YouTube Studio manually:
  set VIRALOS_ENABLE_M32_READONLY_CHECK=1
  python tools/m32_reconcile_unknown.py --intent-id ID --video-id ABCDEFGHIjk \
    --confirm-readonly-network I_AUTHORIZE_READONLY_CHECK \
    --confirm-checked-studio I_CHECKED_PRIVATE_AND_DISCLOSURE \
    --confirm-reconcile I_RECONCILE_EXISTING_INTENT_ONLY \
    --reviewer Owner --evidence-output C:/Private/new-m32-reconciliation.json

Evidence and tokens remain LOCAL; never commit owner reports or keys to Git.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app import db
from app.m32_acceptance import VIDEO_ID
from app.m32_recovery import reconcile_unknown
from tools.m32_private_acceptance import verify_live


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--intent-id',required=True)
    p.add_argument('--video-id',required=True)
    p.add_argument('--reviewer',required=True)
    p.add_argument('--evidence-output',required=True,type=Path)
    p.add_argument('--confirm-readonly-network',required=True,choices=['I_AUTHORIZE_READONLY_CHECK'])
    p.add_argument('--confirm-checked-studio',required=True,choices=['I_CHECKED_PRIVATE_AND_DISCLOSURE'])
    p.add_argument('--confirm-reconcile',required=True,choices=['I_RECONCILE_EXISTING_INTENT_ONLY'])
    args=p.parse_args(argv)
    if os.getenv('VIRALOS_ENABLE_M32_READONLY_CHECK')!='1':
        p.error('Owner must opt in locally: VIRALOS_ENABLE_M32_READONLY_CHECK=1')
    if not VIDEO_ID.fullmatch(args.video_id):p.error('Invalid remote video ID')
    dest=args.evidence_output.resolve()
    if dest.is_relative_to(Path(__file__).resolve().parent.parent) or dest.exists():
        p.error('Use a NEW private evidence path outside public source')
    with db.read() as c:
        intent=db.one(c,'SELECT * FROM m3_private_upload_intents WHERE intent_id=?',(args.intent_id,))
    if not intent or intent['state']!='REMOTE_UNKNOWN':
        p.error('Only an existing REMOTE_UNKNOWN intent can be reconciled')
    if intent['remote_video_id'] and intent['remote_video_id']!=args.video_id:
        p.error('Recorded remote video ID differs from supplied video')
    verification,analytics=verify_live(intent,args.video_id,None,None)
    if not verification['metadata_verified'] or verification['privacy_status']!='private':
        p.error('Live private video metadata mismatch: stop; no retry or state change')
    dest.parent.mkdir(parents=True,exist_ok=True)
    observed=datetime.now(timezone.utc).isoformat(timespec='seconds')
    with db.transaction() as c:
        result=reconcile_unknown(c,args.intent_id,args.video_id,verification,
                                 reviewer=args.reviewer,owner_checked_studio=True,
                                 readonly_oauth_verified=True,observed_at_utc=observed)
    # SQLite transaction contains the durable event even if this local file
    # cannot be created. Private evidence file has hashed IDs only.
    with dest.open('x',encoding='utf8') as f:
        json.dump({'schema':'VIRALOS_M32_READONLY_RECONCILIATION_V1',**result,
                   'observed_at_utc':observed,'analytics':{'state':'NOT_REQUESTED'},
                   'external_account_or_privacy_mutated':False},f,ensure_ascii=False,indent=2)
        f.write('\n')
    print('REMOTE_UNKNOWN reconciled to UPLOADED_PRIVATE without new upload; release approval STILL pending.')
    print('Local evidence file:',dest)

if __name__=='__main__':main()
