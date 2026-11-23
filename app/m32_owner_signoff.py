"""Bind an existing read-only M3.2 OAuth report to a separate Studio review.

This does not authenticate evidence against Google or the person making the
review. It does NOT upload, schedule, publish, change privacy or certify legal
rights. Output contains hashes rather than private IDs, viewer metrics or notes.
"""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone

_SHA=re.compile(r'^[a-f0-9]{64}$')
_FLAGS=('watched_full_video_with_audio_in_studio',
        'confirmed_studio_privacy_is_private',
        'confirmed_title_description_disclosures',
        'reviewed_copyright_policy_warnings',
        'confirmed_correct_owner_channel')


def combine_readonly_studio_evidence(api_evidence: dict, studio: dict,
                                     *, now_utc: datetime | None = None) -> dict:
    if not isinstance(api_evidence,dict) or api_evidence.get('gate')!='M3.2_PRIVATE_REAL_ACCOUNT_ACCEPTANCE':
        raise ValueError('M3.2 read-only acceptance record required')
    for key in ('video_id_sha256','account_id_sha256'):
        if not isinstance(api_evidence.get(key),str) or not _SHA.fullmatch(api_evidence[key]):
            raise ValueError('Unverifiable redacted owner/channel identity')
    observed=api_evidence.get('at_utc')
    if not isinstance(observed,str):raise ValueError('Missing UTC observation timestamp')
    try:stamp=datetime.fromisoformat(observed)
    except ValueError as e:raise ValueError('Invalid UTC observation timestamp') from e
    if stamp.tzinfo is None or stamp.utcoffset().total_seconds()!=0:
        raise ValueError('Observation must be UTC')
    now=now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset().total_seconds()!=0:
        raise ValueError('Comparison clock must be UTC aware')
    blockers=[]
    if not 0 <= (now-stamp).total_seconds() <= 30*24*3600:
        blockers.append('READONLY_API_OBSERVATION_EXPIRED_OR_IN_FUTURE')
    checks=api_evidence.get('video_read_only_checks')
    if not isinstance(checks,dict):raise ValueError('Video read-only checks missing')
    if api_evidence.get('live_api_verified') is not True or checks.get('read_only_verification') is not True:
        blockers.append('LIVE_READONLY_OAUTH_VERIFICATION_UNCONFIRMED')
    if (checks.get('metadata_verified') is not True or checks.get('privacy_status')!='private' or
            checks.get('failures')!=[]):
        blockers.append('PRIVATE_METADATA_IDENTITY_VERIFICATION_NOT_PASSED')
    if api_evidence.get('duplicate_upload_attempted') is not False or \
            api_evidence.get('privacy_change_attempted') is not False:
        blockers.append('UNSAFE_UPLOAD_OR_PRIVACY_CHANGE_RECORDED')
    if api_evidence.get('upload_state')!='UPLOADED_PRIVATE' or api_evidence.get('manual_reconcile_required') is True:
        blockers.append('PRIVATE_UPLOAD_NOT_SAFELY_RECONCILED')
    if not isinstance(studio,dict) or set(studio)!=set(_FLAGS)|{'reviewer_id','review_notes'}:
        raise ValueError('Exact human Studio checklist required')
    for field in _FLAGS:
        if studio[field] is not True:
            blockers.append('OWNER_STUDIO_'+field.upper()+'_NOT_CONFIRMED')
    who,notes=studio['reviewer_id'],studio['review_notes']
    if not isinstance(who,str) or not 3<=len(who.strip())<=100 or \
            not isinstance(notes,str) or not 20<=len(notes.strip())<=1500:
        raise ValueError('Named owner reviewer and detailed private notes required')
    analytics=api_evidence.get('analytics')
    if not isinstance(analytics,dict):raise ValueError('Missing analytics observation state')
    analytics_state=analytics.get('state')
    if analytics_state!='LIVE_READONLY_REPORT_RECEIVED' or \
            analytics.get('live_channel_verified') is not True or \
            not isinstance(analytics.get('rows'),list) or not analytics['rows']:
        blockers.append('REAL_OWNER_ANALYTICS_REPORT_NOT_YET_OBSERVED')
    report_hash=hashlib.sha256(json.dumps(api_evidence,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    notes_hash=hashlib.sha256(notes.encode()).hexdigest()
    return {'schema':'VIRALOS_M32_OWNER_STUDIO_SIGNOFF_V1',
            'state':'OWNER_STUDIO_AND_READONLY_DATA_ATTESTED_NEEDS_EXTERNAL_ACCEPTANCE'
            if not blockers else 'PENDING_OR_BLOCKED',
            'blockers':sorted(set(blockers)),
            'readonly_report_sha256':report_hash,
            'video_id_sha256':api_evidence['video_id_sha256'],
            'account_id_sha256':api_evidence['account_id_sha256'],
            'reviewer_id_sha256':hashlib.sha256(who.strip().casefold().encode()).hexdigest(),
            'private_review_notes_sha256':notes_hash,
            'observed_utc':stamp.isoformat(),
            'analytics_rows_declared':len(analytics.get('rows',[])) if isinstance(analytics.get('rows'),list) else 0,
            'studio_attestation_recorded':True,
            'live_api_proven_by_this_offline_tool':False,
            'studio_identity_independently_verified':False,
            'analytics_values_independently_authenticated_by_this_tool':False,
            'copyright_legality_certified':False,'release_accepted':False,
            'public_publishing_enabled':False,'account_write_or_network_actions':False}
