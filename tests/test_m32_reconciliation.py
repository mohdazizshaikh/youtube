"""M3.2 REMOTE_UNKNOWN never retries upload; only an explicit read-only reconciliation."""
from __future__ import annotations
import sqlite3
import pytest
from app.m32_recovery import reconcile_unknown
from app.m32_acceptance import verify_private_snapshot

VIDEO='ABCDEFGHIjk'
CHANNEL='UCverifiedOwneRchannel'


def db_conn():
    c=sqlite3.connect(':memory:')
    c.row_factory=sqlite3.Row
    c.executescript('''
        CREATE TABLE m3_private_upload_intents (
            intent_id TEXT PRIMARY KEY, state TEXT NOT NULL,
            remote_channel_id TEXT NOT NULL, remote_video_id TEXT,
            receipt_json TEXT, updated_at TEXT
        );
        CREATE TABLE m32_remote_reconciliations (
            reconciliation_id TEXT PRIMARY KEY,intent_id TEXT UNIQUE NOT NULL,
            video_id_sha256 TEXT,verification_sha256 TEXT,reviewer TEXT,
            observed_at_utc TEXT,owner_studio_attested INTEGER,readonly_oauth_verified INTEGER,
            created_at TEXT
        );
    ''')
    c.execute('INSERT INTO m3_private_upload_intents(intent_id,state,remote_channel_id) VALUES (?,?,?)',
              ('intent-fixture','REMOTE_UNKNOWN',CHANNEL))
    return c


def verification():
    expected={'video_id':VIDEO,'channel_id':CHANNEL,'title':'Owner study',
              'description':'Owner-provided original description','tags':[],
              'made_for_kids':False,'altered_content':True}
    snapshot={'id':VIDEO,'snippet':{'channelId':CHANNEL,'title':expected['title'],
                 'description':expected['description'],'tags':[]},
              'status':{'privacyStatus':'private','selfDeclaredMadeForKids':False,
                        'containsSyntheticMedia':True}}
    return verify_private_snapshot(snapshot,expected)


def reconcile(c, result=None, studio=True, oauth=True, video_id=VIDEO):
    return reconcile_unknown(c,'intent-fixture',video_id,result or verification(),
                             reviewer='Owner unit test',owner_checked_studio=studio,
                             readonly_oauth_verified=oauth,
                             observed_at_utc='2026-11-24T00:00:00+00:00')


def test_unknown_recovery_only_with_live_private_owner_studio_confirmation():
    c=db_conn()
    with pytest.raises(ValueError,match='Live authorized'):
        reconcile(c,oauth=False)
    with pytest.raises(ValueError,match='Live authorized'):
        reconcile(c,studio=False)
    assert c.execute('SELECT state FROM m3_private_upload_intents').fetchone()[0]=='REMOTE_UNKNOWN'
    result=reconcile(c)
    assert result['state']=='UPLOADED_PRIVATE' and not result['reuploaded']
    assert result['final_release_accepted'] is False
    assert c.execute('SELECT COUNT(*) FROM m32_remote_reconciliations').fetchone()[0]==1
    assert c.execute('SELECT remote_video_id FROM m3_private_upload_intents').fetchone()[0]==VIDEO
    with pytest.raises(ValueError,match='REMOTE_UNKNOWN'):
        reconcile(c)
    c.close()


def test_unknown_recovery_refuses_public_wrong_channel_wrong_video_and_missing_metadata():
    c=db_conn()
    for changes in ({'privacy_status':'public'},{'remote_channel_id':'different'},
                    {'metadata_verified':False},{'failures':['NOT_PRIVATE']},
                    {'remote_video_id':'zzzzzzzzzzz'}):
        result={**verification(),**changes}
        with pytest.raises(ValueError,match='did not pass'):
            reconcile(c,result)
    with pytest.raises(ValueError,match='Invalid YouTube'):
        reconcile(c,video_id='not-a-valid-video-id')
    assert c.execute('SELECT COUNT(*) FROM m32_remote_reconciliations').fetchone()[0]==0
    assert c.execute('SELECT state FROM m3_private_upload_intents').fetchone()[0]=='REMOTE_UNKNOWN'
    c.close()
