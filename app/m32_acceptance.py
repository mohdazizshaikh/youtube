"""M3.2 strictly read-only real-account YouTube acceptance verification.

No upload, delete, privacy change, or external write is implemented. A valid
public API fixture cannot prove live acceptance. Actual results require the
owner's separately authorized OAuth credentials and an existing PRIVATE video.
"""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
import re

VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')


def verify_private_snapshot(video: dict, expected: dict) -> dict:
    """Compare a `videos.list(part=snippet,status)` result with the owner's intent.

    Fail closed on absent privacy/channel/metadata. YouTube may withhold some
    optional synthetic disclosures; flag that for manual review, never assume.
    """
    if not isinstance(video, dict) or not isinstance(expected, dict):
        raise ValueError('Expected YouTube video and local upload intent dictionaries')
    expected_id = expected.get('video_id')
    if not isinstance(expected_id, str) or not VIDEO_ID.fullmatch(expected_id):
        raise ValueError('Video ID must be eleven URL-safe characters')
    failures = []
    status = video.get('status') or {}
    snippet = video.get('snippet') or {}
    if video.get('id') != expected_id:
        failures.append('VIDEO_ID_MISMATCH')
    if not expected.get('channel_id') or snippet.get('channelId') != expected.get('channel_id'):
        failures.append('OWNED_CHANNEL_MISMATCH')
    if status.get('privacyStatus') != 'private':
        failures.append('NOT_PRIVATE')
    if snippet.get('title') != expected.get('title'):
        failures.append('TITLE_MISMATCH')
    if snippet.get('description') != expected.get('description'):
        failures.append('DESCRIPTION_MISMATCH')
    remote_tags = [str(x).strip().casefold() for x in snippet.get('tags', [])]
    intended_tags = [str(x).strip().casefold() for x in expected.get('tags', [])]
    if sorted(remote_tags) != sorted(intended_tags):
        failures.append('TAGS_MISMATCH')
    if status.get('selfDeclaredMadeForKids') is None:
        failures.append('MISSING_KIDS_DECLARATION')
    elif bool(status['selfDeclaredMadeForKids']) != bool(expected.get('made_for_kids')):
        failures.append('KIDS_DECLARATION_MISMATCH')
    human_checks = []
    if status.get('containsSyntheticMedia') is None:
        human_checks.append('SYNTHETIC_DISCLOSURE_NOT_RETURNED_CONFIRM_STUDIO')
    elif bool(status['containsSyntheticMedia']) != bool(expected.get('altered_content')):
        failures.append('SYNTHETIC_DISCLOSURE_MISMATCH')
    return {'metadata_verified': not failures, 'privacy_status': status.get('privacyStatus', 'MISSING'),
            'failures': failures, 'studio_manual_checks': human_checks,
            'remote_video_id': expected_id, 'remote_channel_id': expected.get('channel_id'),
            'read_only_verification': True, 'live_evidence_required': True,
            'public_upload_or_privacy_change_performed': False}


def acceptance_record(*, result: dict, intent_id: str, upload_state: str,
                      video_id: str, account_id: str, live_api_verified: bool,
                      analytics: dict | None = None) -> dict:
    if upload_state not in ('UPLOADED_PRIVATE', 'REMOTE_UNKNOWN'):
        raise ValueError('Acceptance applies only to uploaded or remotely unknown intents')
    return {
        'gate': 'M3.2_PRIVATE_REAL_ACCOUNT_ACCEPTANCE',
        'at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'intent_id': intent_id,
        # Hash IDs for the shareable evidence; owner keeps full IDs locally.
        'video_id_sha256': hashlib.sha256(video_id.encode()).hexdigest(),
        'account_id_sha256': hashlib.sha256(account_id.encode()).hexdigest(),
        'upload_state': upload_state,
        'live_api_verified': live_api_verified,
        'video_read_only_checks': {key: value for key, value in result.items()
                                   if key not in ('remote_video_id','remote_channel_id')},
        'analytics': analytics or {'state':'NOT_TESTED'},
        'duplicate_upload_attempted': False,
        'privacy_change_attempted': False,
        'owner_studio_review_required': True,
        'manual_reconcile_required': upload_state == 'REMOTE_UNKNOWN',
        'release_accepted': False,
    }
