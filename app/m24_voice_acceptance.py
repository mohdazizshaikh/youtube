"""Offline listening review of an **existing** locally rendered Piper draft.

The software can establish PCM technical quality and exact bytes, but it cannot
hear or authenticate a human reviewer. A passing record is a *self-attestation*
only, NEVER certification of naturalness, commercial voice rights, or release.
No accounts, models, external services, cloning, or publication are accessed.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .m24_audio import wav_audio_qa

_SHA = re.compile(r'^[0-9a-f]{64}$')
_NATIVE = {'hi-IN': 'hi', 'en-US': 'en', 'en-IN': 'en'}
_REQUIRED_FLAGS = ('listened_to_entire_audio', 'checked_against_original_script',
                   'checked_names_numbers_units', 'checked_pronunciation_and_pacing',
                   'checked_speaker_consent_and_usage_rights')
_REVIEW_KEYS = set(_REQUIRED_FLAGS) | {'reviewer_id', 'native_language',
                                      'naturalness_score', 'intelligibility_score',
                                      'artifact_free_score', 'notes'}


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def evaluate_voice_review(draft: dict, wav_path: Path, reviews: list[dict]) -> dict:
    if not isinstance(draft, dict) or draft.get('status') != 'DRAFT_SYNTHESIZED_OWNER_LISTENING_REQUIRED':
        raise ValueError('Real local Piper draft synthesis report required')
    locale = draft.get('locale')
    if locale not in _NATIVE:
        raise ValueError('Unsupported voice locale')
    for key in ('audio_sha256','model_sha256','config_sha256','binary_sha256','text_sha256'):
        value = draft.get(key)
        if not isinstance(value, str) or not _SHA.fullmatch(value):
            raise ValueError('Missing hashed Piper provenance: '+key)
    path = Path(wav_path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Voice WAV must be a local regular non-symlink file')
    qa = wav_audio_qa(path)
    if qa['audio_sha256'] != draft['audio_sha256']:
        raise ValueError('Voice WAV differs from the Piper synthesis report')
    previous_qa = draft.get('audio_qa')
    if not isinstance(previous_qa, dict) or previous_qa.get('duration_ms') != qa['duration_ms'] or \
            previous_qa.get('audio_sha256') != qa['audio_sha256']:
        raise ValueError('Recorded and measured audio QA do not match')
    if not isinstance(reviews, list) or not 1 <= len(reviews) <= 8:
        raise ValueError('Provide 1..8 individual human listening declarations')
    review_ids = set()
    individual = []
    blockers = []
    for index, review in enumerate(reviews):
        if not isinstance(review, dict) or set(review) != _REVIEW_KEYS:
            raise ValueError('Unknown/missing listening review fields')
        rid = review['reviewer_id']
        if not isinstance(rid, str) or not 3 <= len(rid.strip()) <= 100 or any(ord(ch) < 32 for ch in rid):
            raise ValueError('Named reviewer ID required')
        rid_key = rid.strip().casefold()
        if rid_key in review_ids:
            raise ValueError('Repeated reviewer cannot count as independent listeners')
        review_ids.add(rid_key)
        native = review['native_language'] == _NATIVE[locale]
        if not native:
            blockers.append(f'REVIEW_{index}_NOT_TARGET_NATIVE_LANGUAGE')
        false_flags = [name for name in _REQUIRED_FLAGS if review[name] is not True]
        blockers.extend(f'REVIEW_{index}_{name.upper()}_NOT_ATTESTED' for name in false_flags)
        for field in ('naturalness_score', 'intelligibility_score', 'artifact_free_score'):
            if type(review[field]) is not int or not 1 <= review[field] <= 5:
                raise ValueError('Listening scores must be integers 1..5')
            if review[field] < 4:
                blockers.append(f'REVIEW_{index}_{field.upper()}_BELOW_4')
        note = review['notes']
        if not isinstance(note, str) or not 20 <= len(note.strip()) <= 1500:
            raise ValueError('Each human reviewer must enter descriptive private notes')
        # Only salted? No: hash IDs and notes independently but never disclose raw private notes.
        individual.append({'reviewer_id_sha256':hashlib.sha256(rid_key.encode()).hexdigest(),
                           'native_language_attested':native,
                           'scores':{field:review[field] for field in
                                     ('naturalness_score','intelligibility_score','artifact_free_score')},
                           'review_notes_sha256':hashlib.sha256(note.encode()).hexdigest(),
                           'mandatory_listening_checks_attested':not false_flags})
    if len(reviews) < 2:
        blockers.append('AT_LEAST_TWO_DISTINCT_NATIVE_LISTENERS_REQUIRED')
    if qa['technical_flags']:
        blockers.extend('TECHNICAL_AUDIO_'+x for x in qa['technical_flags'])
    result = {'schema':'VIRALOS_M24_HUMAN_VOICE_REVIEW_V1',
              'status':'HUMAN_LISTENING_ATTESTED_NOT_INDEPENDENTLY_VERIFIED' if not blockers else
                       'VOICE_REVIEW_NOT_READY',
              'locale':locale, 'audio_sha256':qa['audio_sha256'],
              'text_sha256':draft['text_sha256'], 'model_sha256':draft['model_sha256'],
              'config_sha256':draft['config_sha256'], 'binary_sha256':draft['binary_sha256'],
              'audio_technical_qa':qa, 'reviewers':individual, 'reviewer_count':len(individual),
              'blockers':sorted(set(blockers)),
              'actual_wav_bytes_verified':True, 'speaker_licence_independently_verified':False,
              'human_review_identity_independently_verified':False,
              'listening_actually_performed_verified_by_software':False,
              'naturalness_independently_certified':False,
              'youtube_upload_authorized':False, 'automatic_publishing_enabled':False,
              'network_calls':False}
    return result
