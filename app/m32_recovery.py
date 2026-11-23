"""M3.2 manual reconciliation of a REMOTE_UNKNOWN upload: NEVER reupload.

The calling owner-only CLI obtains a read-only OAuth video snapshot *before*
calling this function. It cannot independently prove that caller-provided
verification dictionaries came from Google; the real CLI is the acceptance
path. A reconciliation confirms known upload state, NOT creative/legal release.
"""
from __future__ import annotations
import hashlib
import json
from . import db
from .m32_acceptance import VIDEO_ID


def reconcile_unknown(c, intent_id: str, video_id: str, verification: dict,
                      *, reviewer: str, owner_checked_studio: bool,
                      readonly_oauth_verified: bool, observed_at_utc: str) -> dict:
    if not readonly_oauth_verified or not owner_checked_studio:
        raise ValueError('Live authorized READONLY video check and manual YouTube Studio review required')
    if not isinstance(reviewer,str) or not 2 <= len(reviewer.strip()) <= 100:
        raise ValueError('Named human reviewer required')
    if not isinstance(observed_at_utc,str) or not observed_at_utc.endswith('+00:00'):
        raise ValueError('UTC observation timestamp required')
    if not isinstance(video_id,str) or not VIDEO_ID.fullmatch(video_id):
        raise ValueError('Invalid YouTube video ID')
    intent=db.one(c,'SELECT * FROM m3_private_upload_intents WHERE intent_id=?',(intent_id,))
    if not intent or intent['state']!='REMOTE_UNKNOWN':
        raise ValueError('Only an existing REMOTE_UNKNOWN intent can be reconciled')
    if intent['remote_video_id'] and intent['remote_video_id']!=video_id:
        raise ValueError('Recorded video differs from owner verified video')
    if (verification.get('remote_video_id')!=video_id or
        verification.get('remote_channel_id')!=intent['remote_channel_id'] or
        verification.get('privacy_status')!='private' or
        verification.get('metadata_verified') is not True or
        verification.get('failures') != [] or
        verification.get('read_only_verification') is not True):
        raise ValueError('Live private video metadata/channel verification did not pass')
    already=db.one(c,'SELECT reconciliation_id FROM m32_remote_reconciliations WHERE intent_id=?',(intent_id,))
    if already:
        raise ValueError('Intent has an existing reconciliation event')
    from . import main as m
    rid=m.uid()
    digest=hashlib.sha256(json.dumps(verification,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    c.execute('INSERT INTO m32_remote_reconciliations '
              '(reconciliation_id,intent_id,video_id_sha256,verification_sha256,reviewer,observed_at_utc,'
              'owner_studio_attested,readonly_oauth_verified,created_at) VALUES (?,?,?,?,?,?,?,?,?)',
              (rid,intent_id,hashlib.sha256(video_id.encode()).hexdigest(),digest,reviewer.strip(),
               observed_at_utc,1,1,m.now()))
    receipt={'id':video_id,'privacyStatus':'private',
             'reconciled_from_unknown_via_readonly_oauth':True,
             'verification_sha256':digest,'reconciliation_id':rid,
             'owner_studio_reviewed':True}
    result=c.execute("UPDATE m3_private_upload_intents SET state='UPLOADED_PRIVATE',"
                     "remote_video_id=?,receipt_json=?,updated_at=? WHERE intent_id=? AND state='REMOTE_UNKNOWN'",
                     (video_id,m.j(receipt),m.now(),intent_id))
    if result.rowcount != 1:
        raise ValueError('Concurrent intent state change: nothing reconciled')
    return {'reconciliation_id':rid,'intent_id':intent_id,'state':'UPLOADED_PRIVATE',
            'verification_sha256':digest,'video_id_sha256':hashlib.sha256(video_id.encode()).hexdigest(),
            'reuploaded':False,'privacy_change_performed':False,'live_readonly_video_check_claimed':True,
            'owner_studio_manual_confirmation_recorded':True,
            'analytics_and_monetization_accepted':False,'final_release_accepted':False}
