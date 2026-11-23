#!/usr/bin/env python3
"""M3.2 owner-supervised, read-only YouTube acceptance proof.

This tool NEVER uploads a file, schedules a video or changes privacy. The
operator must already have completed the independent, opt-in M3 PRIVATE upload.
Only run on the owner's machine with existing keyring-backed OAuth credentials.

Example:
  set VIRALOS_ENABLE_M32_READONLY_CHECK=1
  python tools/m32_private_acceptance.py --intent-id ID --video-id ABCDEFGHIjk \
      --confirm-readonly-network I_AUTHORIZE_READONLY_CHECK --output local-evidence.json

Optional --analytics-start YYYY-MM-DD --analytics-end YYYY-MM-DD requires a
separate authorized Analytics OAuth account. Do NOT commit local evidence,
OAuth JSON, client secrets or private video URLs to GitHub.
"""
from __future__ import annotations
import argparse, json, os, sys
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import db
from app.m32_acceptance import verify_private_snapshot, acceptance_record, VIDEO_ID


def verify_live(intent: dict, video_id: str, analytics_start: str | None, analytics_end: str | None):
    from googleapiclient.discovery import build
    from app.youtube_private import upload_credentials, verify_owned_channel
    from app.youtube_analytics import credentials_for, verify_channel, fetch_daily_report, normalize_report
    credentials = upload_credentials(intent['local_channel_id'])
    owned = verify_owned_channel(credentials, intent['remote_channel_id'])
    if owned['id'] != intent['remote_channel_id']:
        raise RuntimeError('Authenticated channel is not the requested owner channel')
    service=build('youtube','v3',credentials=credentials,cache_discovery=False)
    response=service.videos().list(part='snippet,status',id=video_id).execute()
    videos=response.get('items', [])
    if len(videos)!=1:
        raise RuntimeError('Video not visible through this authorized account; do not retry upload')
    expected={'video_id':video_id,'channel_id':intent['remote_channel_id'],
              'title':intent['title'],'description':intent['description'],
              'tags':json.loads(intent['tags_json']),
              'altered_content':bool(intent['altered_content']),
              'made_for_kids':bool(intent['made_for_kids'])}
    verification=verify_private_snapshot(videos[0],expected)
    analytics={'state':'NOT_REQUESTED'}
    if analytics_start is not None:
        if date.fromisoformat(analytics_start)>date.fromisoformat(analytics_end):
            raise ValueError('Analytics start date must be before/end date')
        acl=credentials_for(intent['local_channel_id'])
        verified=verify_channel(acl,intent['remote_channel_id'])
        if verified['id']!=intent['remote_channel_id']:
            raise RuntimeError('Analytics OAuth channel differs from upload channel')
        report=normalize_report(fetch_daily_report(acl,analytics_start,analytics_end))
        analytics={'state':'LIVE_READONLY_REPORT_RECEIVED' if report else 'LIVE_EMPTY_REPORT_PENDING',
                   'rows':report, 'live_channel_verified':True,
                   'revenue_reported':False}
    return verification,analytics


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--intent-id',required=True)
    p.add_argument('--video-id',required=True)
    p.add_argument('--confirm-readonly-network',choices=['I_AUTHORIZE_READONLY_CHECK'],required=True)
    p.add_argument('--analytics-start')
    p.add_argument('--analytics-end')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(argv)
    if os.environ.get('VIRALOS_ENABLE_M32_READONLY_CHECK')!='1':
        p.error('Explicit local VIRALOS_ENABLE_M32_READONLY_CHECK=1 is required')
    if bool(args.analytics_start)!=bool(args.analytics_end):
        p.error('Both analytics-start and analytics-end are required together')
    if not VIDEO_ID.fullmatch(args.video_id):
        p.error('YouTube video ID must be eleven URL-safe characters')
    with db.read() as c:
        intent=db.one(c,'SELECT * FROM m3_private_upload_intents WHERE intent_id=?',(args.intent_id,))
    if not intent or intent['state'] not in ('UPLOADED_PRIVATE','REMOTE_UNKNOWN'):
        p.error('Only a committed uploaded/remote-unknown private intent can be verified')
    if intent['remote_video_id'] and intent['remote_video_id']!=args.video_id:
        p.error('Remote video ID differs from recorded intent: manual reconciliation required')
    if args.output.exists():
        p.error('Evidence output already exists: never overwrite a prior acceptance observation')
    verification,analytics=verify_live(intent,args.video_id,args.analytics_start,args.analytics_end)
    record=acceptance_record(result=verification,intent_id=args.intent_id,
                             upload_state=intent['state'],video_id=args.video_id,
                             account_id=intent['remote_channel_id'],live_api_verified=True,
                             analytics=analytics)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    # Local evidence file, intentionally untracked and without tokens/raw IDs.
    with args.output.open('x',encoding='utf8') as f:
        json.dump(record,f,ensure_ascii=False,indent=2)
    if not verification['metadata_verified'] or verification['privacy_status']!='private':
        raise RuntimeError('Private video verification FAILED. Review evidence; do not upload again.')
    print('Read-only remote PRIVATE metadata verified; Studio and human release acceptance still pending.')
    print('Local audit:',args.output)
    if record['manual_reconcile_required']:
        print('REMOTE_UNKNOWN: reconcile upload intent manually; do not issue a duplicate upload.')


if __name__=='__main__':
    main()
