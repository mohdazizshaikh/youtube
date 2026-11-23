"""Synthetic API fixtures test software gate only, NOT real OAuth or Studio review."""
import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime,timezone,timedelta
from pathlib import Path
import pytest
from app.m32_owner_signoff import combine_readonly_studio_evidence
from app.m32_acceptance import acceptance_record,verify_private_snapshot


def fixture(now):
    video='ABCDEFGHIjk';channel='UCsyntheticOwner'
    exp={'video_id':video,'channel_id':channel,'title':'Original private demo','description':'Original analysis project.',
         'tags':['original'],'made_for_kids':False,'altered_content':False}
    live={'id':video,'snippet':{'channelId':channel,'title':exp['title'],'description':exp['description'],'tags':['original']},
          'status':{'privacyStatus':'private','selfDeclaredMadeForKids':False,'containsSyntheticMedia':False}}
    checks=verify_private_snapshot(live,exp)
    api=acceptance_record(result=checks,intent_id='intent-synthetic',upload_state='UPLOADED_PRIVATE',
                          video_id=video,account_id=channel,live_api_verified=True,
                          analytics={'state':'LIVE_READONLY_REPORT_RECEIVED','live_channel_verified':True,
                                     'rows':[{'report_date':'2026-11-23','views':1,'watch_hours':0.25,'subscribers_gained':0}]})
    api['at_utc']=now.isoformat(timespec='seconds')
    owner={'reviewer_id':'Synthetic owner reviewer',
           'review_notes':'Synthetic unit test only, never proof of a real Studio action.',
           'watched_full_video_with_audio_in_studio':True,
           'confirmed_studio_privacy_is_private':True,
           'confirmed_title_description_disclosures':True,
           'reviewed_copyright_policy_warnings':True,
           'confirmed_correct_owner_channel':True}
    return api,owner


def test_studio_signoff_links_live_report_without_promising_release():
    now=datetime(2026,11,24,1,0,tzinfo=timezone.utc)
    api,studio=fixture(now)
    r=combine_readonly_studio_evidence(api,studio,now_utc=now)
    assert r['state'].startswith('OWNER_STUDIO') and r['blockers']==[]
    assert r['analytics_rows_declared']==1
    assert not r['live_api_proven_by_this_offline_tool']
    assert not r['release_accepted']
    assert 'Synthetic owner reviewer' not in json.dumps(r)
    assert 'watch_hours' not in json.dumps(r)


def test_studio_signoff_blocks_unknown_remote_and_no_analytics():
    now=datetime(2026,11,24,1,0,tzinfo=timezone.utc)
    api,studio=fixture(now)
    api.update(upload_state='REMOTE_UNKNOWN',manual_reconcile_required=True)
    api['analytics']={'state':'NOT_REQUESTED'}
    result=combine_readonly_studio_evidence(api,studio,now_utc=now)
    assert 'PRIVATE_UPLOAD_NOT_SAFELY_RECONCILED' in result['blockers']
    assert 'REAL_OWNER_ANALYTICS_REPORT_NOT_YET_OBSERVED' in result['blockers']
    assert result['state']=='PENDING_OR_BLOCKED'


def test_bad_channel_privacy_and_stale_timestamp_fail_closed():
    now=datetime(2026,11,24,1,0,tzinfo=timezone.utc)
    api,studio=fixture(now)
    api['at_utc']=(now-timedelta(days=31)).isoformat()
    api['video_read_only_checks']['privacy_status']='public'
    studio['confirmed_studio_privacy_is_private']=False
    out=combine_readonly_studio_evidence(api,studio,now_utc=now)
    assert 'READONLY_API_OBSERVATION_EXPIRED_OR_IN_FUTURE' in out['blockers']
    assert 'PRIVATE_METADATA_IDENTITY_VERIFICATION_NOT_PASSED' in out['blockers']
    assert any('OWNER_STUDIO_' in item for item in out['blockers'])
    api['at_utc']='NOT A DATE'
    with pytest.raises(ValueError,match='UTC observation'):
        combine_readonly_studio_evidence(api,studio,now_utc=now)


def test_studio_signoff_cli_immutable_report_synthetic(tmp_path):
    now=datetime.now(timezone.utc)
    api,studio=fixture(now)
    raw=tmp_path/'api.json';raw.write_text(json.dumps(api))
    check=tmp_path/'manual.json';check.write_text(json.dumps(studio))
    output=tmp_path/'signoff.json'
    cmd=[sys.executable,str(Path(__file__).resolve().parents[1]/'tools'/'m32_signoff_studio.py'),
         '--api-evidence',str(raw),'--owner-studio-checklist',str(check),'--output',str(output)]
    first=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
    assert first.returncode==0,first.stderr
    assert json.loads(output.read_text())['release_accepted'] is False
    assert subprocess.run(cmd,capture_output=True,text=True,timeout=15).returncode != 0
