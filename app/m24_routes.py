"""M2.4 per-project acoustic word drafts with mandatory owner-review promotion.

Machine-generated timestamps never bypass the existing M2.2 verified narration,
source, project, or final review gates. Local-only: no speech model is loaded
in FastAPI, and an uploaded claim of external alignment is never treated as
proof of running a model on this machine.
"""
from __future__ import annotations
import json
from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Literal
from . import db
from .m24_audio import SUPPORTED_LOCALES
from .creative_m22 import word_time_check
from .studio_routes import sha_file


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class AcousticWord(Strict):
    token: str = Field(min_length=1,max_length=90)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    acoustic_score: float = Field(ge=0,le=1)

    @model_validator(mode='after')
    def check_times(self):
        if self.end_ms <= self.start_ms:
            raise ValueError('Acoustic word interval must be positive')
        return self


class AlignmentDraftIn(Strict):
    locale: Literal['en-US','en-IN','hi-IN']
    voice_audio_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    model_directory_name: str = Field(min_length=1,max_length=120,pattern=r'^[A-Za-z0-9_. -]+$')
    method: Literal['OFFLINE_CTC_VITERBI_FORCED_ALIGNMENT']
    status: Literal['DRAFT_OWNER_REVIEW_REQUIRED']
    words: list[AcousticWord] = Field(min_length=2,max_length=150)


class OwnerAcceptIn(Strict):
    owner_listened_to_full_audio: Literal[True]
    owner_checked_each_word_and_timing: Literal[True]
    owner_checked_translation_names_numbers: Literal[True]
    reviewer: str = Field(min_length=2,max_length=100)


def _plan_and_audio(c, project_id, plan_id):
    from . import main as m
    p=m.from_project(c,project_id)
    script=m.latest_script(c,project_id)
    plan=db.one(c,'SELECT * FROM m2_studio_plans WHERE plan_id=? AND project_id=?',(plan_id,project_id))
    if not plan or not script or plan['script_version_id']!=script['script_version_id'] or plan['project_revision']!=p['revision']:
        raise HTTPException(409,'Studio plan/script stale or missing')
    audio=db.one(c,'SELECT * FROM m21_plan_audio WHERE plan_id=? AND project_id=?',(plan_id,project_id))
    if not audio:
        raise HTTPException(409,'M2.4 alignment requires measured segment audio from M2.1')
    voice=(m.OUT / audio['voice_relpath']).resolve()
    if m.OUT.resolve() not in voice.parents or not voice.is_file() or sha_file(voice)!=audio['voice_sha256']:
        raise HTTPException(409,'Voice file missing, changed, or outside output directory')
    return p,script,plan,audio


def register_m24_audio(app):
    from . import main as m

    @app.get('/api/m24/capabilities')
    def m24_capabilities():
        return {'stage':'M2.4_LOCAL_CTC_DRAFT_AND_OWNER_REVIEW',
                'local_acoustic_alignment_cli': True,
                'automatic_translation': False,
                'professional_voice_quality_certified': False,
                'offline_piper_optional': True,
                'owner_local_piper_cli_draft_synthesis': True,
                'bundled_professional_voice_models': False,
                'local_ctc_model_bundled': False,
                'model_auto_download': False,
                'supported_locales': sorted(SUPPORTED_LOCALES),
                'owner_review_required': True,
                'ready_for_autonomous_publishing': False}

    @app.post('/api/projects/{project_id}/m24/plans/{plan_id}/alignment-drafts')
    def register_acoustic_draft(project_id: str,plan_id: str,body: AlignmentDraftIn):
        if not all(w.acoustic_score > 0 for w in body.words):
            raise HTTPException(422,'Acoustic score missing: no equal-division synthetic alignment')
        with db.transaction() as c:
            p,script,plan,audio=_plan_and_audio(c,project_id,plan_id)
            if plan['locale']!=body.locale or audio['voice_sha256']!=body.voice_audio_sha256:
                raise HTTPException(409,'Alignment locale/audio SHA does not match immutable plan audio')
            words=[w.model_dump() for w in body.words]
            try:
                word_time_check(json.loads(plan['plan_json']),words)
            except ValueError as ex:
                raise HTTPException(422,'Transcript/timestamps do not match segment captions: '+str(ex)) from ex
            existing=db.one(c,'SELECT draft_id FROM m24_alignment_drafts WHERE plan_id=? AND plan_sha256=? AND voice_sha256=?',
                            (plan_id,plan['plan_sha256'],audio['voice_sha256']))
            if existing:
                raise HTTPException(409,'Alignment draft already exists: review or explicitly create a new project/plan')
            draft_id=m.uid()
            c.execute('INSERT INTO m24_alignment_drafts(draft_id,plan_id,project_id,script_version_id,plan_sha256,voice_sha256,locale,model_name,words_json,status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                      (draft_id,plan_id,project_id,script['script_version_id'],plan['plan_sha256'],audio['voice_sha256'],
                       body.locale,body.model_directory_name,m.j(words),'PENDING_OWNER_REVIEW',m.now()))
        return {'draft_id':draft_id,'state':'PENDING_OWNER_REVIEW','imported_to_m22':False,
                'word_count':len(words),'automatic_source_claim_verification':False,
                'next':'Listen carefully to entire narration and inspect timestamps, then submit owner review.'}

    @app.get('/api/projects/{project_id}/m24/alignment-drafts/{draft_id}')
    def read_draft(project_id:str,draft_id:str):
        with db.read() as c:
            record=db.one(c,'SELECT * FROM m24_alignment_drafts WHERE draft_id=? AND project_id=?',(draft_id,project_id))
            if not record:raise HTTPException(404,'Acoustic alignment draft not found')
            _plan_and_audio(c,project_id,record['plan_id'])
        return {'draft_id':draft_id,'status':record['status'],'locale':record['locale'],
                'model_name':record['model_name'],'words':json.loads(record['words_json']),
                'review_required':record['status']!='OWNER_REVIEWED_IMPORTED'}

    @app.post('/api/projects/{project_id}/m24/alignment-drafts/{draft_id}/owner-review')
    def owner_review(project_id:str,draft_id:str,body:OwnerAcceptIn):
        with db.transaction() as c:
            rec=db.one(c,'SELECT * FROM m24_alignment_drafts WHERE draft_id=? AND project_id=?',(draft_id,project_id))
            if not rec:raise HTTPException(404,'Alignment draft not found')
            if rec['status']!='PENDING_OWNER_REVIEW':raise HTTPException(409,'Already owner-reviewed; never silently overwrite')
            p,script,plan,audio=_plan_and_audio(c,project_id,rec['plan_id'])
            if rec['plan_sha256']!=plan['plan_sha256'] or rec['voice_sha256']!=audio['voice_sha256'] or rec['script_version_id']!=script['script_version_id']:
                raise HTTPException(409,'Alignment draft became stale before human review')
            if db.one(c,'SELECT alignment_id FROM m22_word_alignments WHERE plan_id=?',(rec['plan_id'],)):
                raise HTTPException(409,'Existing owner word alignment cannot be overwritten')
            words=json.loads(rec['words_json'])
            word_time_check(json.loads(plan['plan_json']),words)
            reviewed=[{'token':w['token'],'start_ms':w['start_ms'],'end_ms':w['end_ms']} for w in words]
            aid=m.uid()
            c.execute('INSERT INTO m22_word_alignments(alignment_id,plan_id,project_id,script_version_id,voice_sha256,plan_sha256,words_json,provenance,submitted_at) VALUES (?,?,?,?,?,?,?,?,?)',
                      (aid,rec['plan_id'],project_id,rec['script_version_id'],rec['voice_sha256'],rec['plan_sha256'],
                       m.j(reviewed),'EXTERNAL_ALIGNER_OWNER_REVIEWED',m.now()))
            c.execute("UPDATE m24_alignment_drafts SET status='OWNER_REVIEWED_IMPORTED',reviewed_at=? WHERE draft_id=?",
                      (m.now(),draft_id))
        return {'alignment_id':aid,'status':'OWNER_REVIEWED_IMPORTED','provenance':'EXTERNAL_ALIGNER_OWNER_REVIEWED',
                'reviewer_attestation':body.reviewer,'publish_ready':False,
                'next':'Continue existing M2.2 final video review and rights/fact gates.'}
