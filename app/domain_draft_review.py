"""Offline per-scene editorial handoff for audited drafts; never a release gate.
A pin binds bytes, not reviewer identity. No network or upload operations.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .domain_draft_audit import audit
from .domain_draft_video import DraftPlan, digest


CHECKS = ('source_accuracy', 'narration_accuracy', 'visual_accuracy', 'asset_rights', 'originality', 'caption_accuracy')

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class SceneReview(Strict):
    scene: int = Field(ge=1, le=8)
    scene_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    checks: dict[str, Literal['PASS','REVISE','NOT_REVIEWED']]
    notes: str = Field(default='', max_length=2000)

    @model_validator(mode='after')
    def check_fields(self):
        if set(self.checks) != set(CHECKS):
            raise ValueError('exact review checklist required')
        if 'REVISE' in self.checks.values() and not self.notes.strip():
            raise ValueError('revision requires a note')
        return self

class Review(Strict):
    schema_version: Literal['VIRALOS_DOMAIN_DRAFT_REVIEW_V1']
    manifest_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    packet_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    reviewer: str = Field(max_length=120)
    scenes: list[SceneReview] = Field(min_length=2,max_length=8)


def _canonical(value: dict) -> str:
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode('utf-8'))


def review_packet(draft: Path, assets: Path, manifest_pin: str) -> dict:
    """Re-run the media audit, and bind exact scene content to a review packet."""
    draft=Path(draft)
    result=audit(draft, assets, manifest_pin)
    # Read the same pinned inputs again, not an untrusted previous audit receipt.
    raw=(draft/'manifest.json').read_bytes()
    if digest(raw)!=manifest_pin: raise ValueError('manifest changed during review')
    manifest=json.loads(raw)
    raw_plan=(draft/'plan.json').read_bytes()
    if digest(raw_plan)!=manifest['files_sha256']['plan.json']:
        raise ValueError('plan changed during review')
    plan=DraftPlan.model_validate_json(raw_plan)
    scenes=[]
    for i,(scene,record) in enumerate(zip(plan.scenes,manifest['scenes']),1):
        entry={'scene':i,'start_ms':record['start_ms'],'end_ms':record['end_ms'],
               'board_file':record['board_file'],'board_sha256':record['board_sha256'],
               'narration_sha256':scene.narration_sha256,'narration_text':scene.narration_text,
               'title':scene.board.title,'claims':[c.model_dump() for c in scene.board.claims],
               'sources':[s.model_dump(mode='json') for s in scene.board.sources],
               'specialist_facts':scene.board.specialist_facts,
               'rights_self_attested':scene.rights_attested}
        entry['scene_sha256']=_canonical(entry)
        scenes.append(entry)
    return {'schema':'VIRALOS_DOMAIN_DRAFT_REVIEW_PACKET_V1','manifest_sha256':manifest_pin,
            'video_sha256':manifest['files_sha256']['draft.mp4'],'domain':result['domain'],
            'format':result['format'],'synthetic_demo':result['synthetic_demo'],
            'scenes':scenes,'technical_audit_passed':True,'publication_eligible':False,
            'human_review_verified':False,'checks':list(CHECKS)}


def template(packet: dict) -> dict:
    return {'schema_version':'VIRALOS_DOMAIN_DRAFT_REVIEW_V1','manifest_sha256':packet['manifest_sha256'],
            'packet_sha256':_canonical(packet),'reviewer':'','scenes':[
                {'scene':s['scene'],'scene_sha256':s['scene_sha256'],
                 'checks':dict.fromkeys(CHECKS,'NOT_REVIEWED'),'notes':''} for s in packet['scenes']]}


def evaluate(draft: Path, assets: Path, manifest_pin: str, submitted: dict) -> dict:
    """Fresh audit every evaluation. No synthetic draft can pass human handoff."""
    review=Review.model_validate(submitted)
    packet=review_packet(draft,assets,manifest_pin)
    if review.manifest_sha256!=manifest_pin or review.packet_sha256!=_canonical(packet):
        raise ValueError('stale or substituted review packet')
    expected={s['scene']:s['scene_sha256'] for s in packet['scenes']}
    seen=set(); blockers=[]
    for s in review.scenes:
        if s.scene in seen or expected.get(s.scene)!=s.scene_sha256:
            raise ValueError('duplicate, unknown or changed scene')
        seen.add(s.scene)
        blockers.extend({'scene':s.scene,'check':k,'reason':s.checks[k]} for k in CHECKS if s.checks[k]!='PASS')
    if seen!=set(expected): raise ValueError('incomplete scene coverage')
    if not review.reviewer.strip(): blockers.append({'reason':'REVIEWER_DECLARATION_MISSING'})
    if packet['synthetic_demo']: blockers.append({'reason':'SYNTHETIC_DEMO_NOT_ELIGIBLE'})
    return {'schema':'VIRALOS_DOMAIN_DRAFT_REVIEW_RESULT_V1','manifest_sha256':manifest_pin,
            'video_sha256':packet['video_sha256'],'review_sha256':_canonical(review.model_dump()),
            'domain':packet['domain'],'format':packet['format'],'scene_count':len(seen),
            'synthetic_demo':packet['synthetic_demo'],'blockers':blockers,
            'self_attested_editorial_checklist_complete':not blockers,
            'publication_eligible':False,'reviewer_identity_verified':False,
            'claims_independently_verified':False,'rights_legally_certified':False}
