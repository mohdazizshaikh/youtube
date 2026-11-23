"""M3.2 no-network acceptance logic; never exercise a real YouTube upload."""
from copy import deepcopy
import pytest
from app.m32_acceptance import verify_private_snapshot, acceptance_record

VIDEO='ABCDEFGHIjk'
CHANNEL='UCmyOwnedExampleChannel'


def fixture():
    expected={'video_id':VIDEO,'channel_id':CHANNEL,'title':'Original cricket explanation',
              'description':'Original video and diagram about the sport.',
              'tags':['analysis','cricket'],'made_for_kids':False,'altered_content':True}
    video={'id':VIDEO,'snippet':{'channelId':CHANNEL,'title':expected['title'],
            'description':expected['description'],'tags':['cricket','analysis']},
           'status':{'privacyStatus':'private','selfDeclaredMadeForKids':False,
                     'containsSyntheticMedia':True}}
    return video,expected


def test_remote_private_video_and_metadata_strict_match():
    video,expected=fixture()
    evidence=verify_private_snapshot(video,expected)
    assert evidence['metadata_verified'] and evidence['privacy_status']=='private'
    assert evidence['failures']==[]
    assert evidence['public_upload_or_privacy_change_performed'] is False


def test_fail_closed_public_mismatched_channel_and_wrong_title():
    video,expected=fixture()
    video['status']['privacyStatus']='public'
    video['snippet']['channelId']='UCsomeoneElse'
    video['snippet']['title']='Misleading'
    check=verify_private_snapshot(video,expected)
    assert {'NOT_PRIVATE','OWNED_CHANNEL_MISMATCH','TITLE_MISMATCH'} <= set(check['failures'])
    assert not check['metadata_verified']


def test_missing_synthetic_status_requires_manual_studio_confirmation():
    video,expected=fixture()
    del video['status']['containsSyntheticMedia']
    check=verify_private_snapshot(video,expected)
    assert check['metadata_verified']
    assert 'SYNTHETIC_DISCLOSURE_NOT_RETURNED_CONFIRM_STUDIO' in check['studio_manual_checks']
    del video['status']['selfDeclaredMadeForKids']
    assert 'MISSING_KIDS_DECLARATION' in verify_private_snapshot(video,expected)['failures']


def test_unknown_upload_requires_reconciliation_and_never_auto_accepts():
    video,expected=fixture()
    check=verify_private_snapshot(video,expected)
    evidence=acceptance_record(result=check,intent_id='mock-intent',upload_state='REMOTE_UNKNOWN',
                               video_id=VIDEO,account_id=CHANNEL,live_api_verified=False)
    assert evidence['manual_reconcile_required']
    assert evidence['live_api_verified'] is False
    assert evidence['release_accepted'] is False
    assert VIDEO not in str(evidence) and CHANNEL not in str(evidence)
    with pytest.raises(ValueError):
        acceptance_record(result=check,intent_id='mock',upload_state='PREPARED',
                          video_id=VIDEO,account_id=CHANNEL,live_api_verified=False)
