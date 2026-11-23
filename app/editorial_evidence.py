"""Evidence-to-release editorial inspection (read-only except owner attestation).

This program tests provenance *metadata*. It cannot validate factual correctness,
licensed footage/music usage, legal compliance or original creative value; the
human must actually inspect the original media and cited sources.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal
from . import db

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

class EditorialReviewIn(Strict):
    final_export_id: str = Field(min_length=2,max_length=100)
    auditor: str = Field(min_length=2,max_length=100)
    notes: str = Field(min_length=20,max_length=4000)
    checked_full_final_video: Literal[True]
    checked_every_material_claim_and_original_source: Literal[True]
    independently_checked_asset_and_music_rights: Literal[True]
    reviewed_originality_and_transformative_value: Literal[True]
    reviewed_ai_disclosure_and_sensitive_subjects: Literal[True]


def calculate(project:dict,script:dict|None,claims:list[dict],links:list[dict],
              evidence:list[dict],media:list[dict],final:list[dict],localized:list[dict]) -> dict:
    blockers=[];advisories=[]
    if script is None:
        blockers.append('SCRIPT_MISSING')
    linked={x['claim_id'] for x in links}
    claims_by_id={x['claim_id']:x for x in claims}
    for cid in sorted(linked):
        c=claims_by_id.get(cid)
        if not c or c['verification_status']!='SUPPORTED':
            blockers.append(f'CLAIM_NOT_SUPPORTED:{cid}')
        if not any(x['claim_id']==cid and x['relation']=='SUPPORTS' for x in evidence):
            blockers.append(f'CLAIM_SUPPORTING_EVIDENCE_MISSING:{cid}')
    if any(x['verification_status']!='SUPPORTED' for x in claims):
        advisories.append('OTHER_PROJECT_CLAIMS_UNRESOLVED')
    if script and not linked:
        advisories.append('SCRIPT_HAS_NO_CLAIM_LINKS_FACT_CHECK_MANUALLY')
    for asset in media:
        if not asset['rights_attested'] or not asset['license_note'].strip():
            blockers.append('MEDIA_RIGHTS_RECORD_INCOMPLETE:'+asset['asset_id'])
        if len(asset['content_sha256'])!=64:
            blockers.append('MEDIA_HASH_MISSING:'+asset['asset_id'])
    if not final:
        blockers.append('OWNER_APPROVED_FINAL_VIDEO_MISSING')
    for row in localized:
        if row['status']!='OWNER_REVIEWED':
            advisories.append('LOCALE_PENDING_OWNER_REVIEW:'+row['locale'])
    advisories += ['LEGAL_RIGHTS_NOT_AUTOMATICALLY_ESTABLISHED',
                   'FACT_CHECK_REQUIRES_INDEPENDENT_READ_OF_SOURCES',
                   'HUMAN_CREATIVE_QUALITY_AND_DISCLOSURE_REQUIRED']
    snapshot={'project':project['project_id'],'project_revision':project['revision'],
              'script_id':script['script_version_id'] if script else None,
              'script_sha':script['content_sha256'] if script else None,
              'claims':claims,'links':links,'evidence':evidence,'media':media,
              'final':final,'localizations':localized}
    digest=hashlib.sha256(json.dumps(snapshot,sort_keys=True,ensure_ascii=False).encode('utf8')).hexdigest()
    return {'status':'BLOCKED' if blockers else 'METADATA_PRESENT_INDEPENDENT_OWNER_REVIEW_REQUIRED',
            'blockers':blockers,'advisories':advisories,'source_assertions_verified_by_program':False,
            'copyright_legality_certified':False,'publication_eligible':False,
            'snapshot_sha256':digest}


def snapshot(c,project_id):
    from . import main as m
    project=m.from_project(c,project_id); script=m.latest_script(c,project_id)
    plan=m._plan(c,project)
    claims=db.many(c,'SELECT claim_id,verification_status,updated_at FROM claims WHERE research_plan_id=? ORDER BY claim_id',(plan['research_plan_id'],))
    links=db.many(c,'SELECT claim_id,span_start,span_end FROM script_claim_links WHERE script_version_id=? ORDER BY claim_id,span_start',(script['script_version_id'],)) if script else []
    evidence=db.many(c,'SELECT claim_id,source_version_id,relation,locator FROM evidence_edges WHERE claim_id IN '
                     '(SELECT claim_id FROM claims WHERE research_plan_id=?) ORDER BY claim_id,source_version_id,locator',(plan['research_plan_id'],))
    media=db.many(c,'SELECT asset_id,rights_attested,license_note,content_sha256 FROM m2_studio_assets WHERE project_id=? ORDER BY asset_id',(project_id,))
    final=db.many(c,'SELECT export_id,review_id,plan_id,fingerprint,file_sha256,status FROM m22_final_exports WHERE project_id=? ORDER BY export_id',(project_id,))
    localized=db.many(c,'SELECT locale,status,content_sha256,dependency_sha256,script_version_id FROM m25_localized_variants '
                      'WHERE project_id=? ORDER BY locale',(project_id,))
    result=calculate(project,script,claims,links,evidence,media,final,localized)
    result['final_export_ids']=[x['export_id'] for x in final]
    return result,script


def register_editorial(app):
    from . import main as m
    @app.get('/api/projects/{project_id}/m26/editorial-audit')
    def editorial_audit(project_id:str):
        with db.read() as c:
            result,_=snapshot(c,project_id)
        return result

    @app.post('/api/projects/{project_id}/m26/editorial-owner-review')
    def editorial_owner_review(project_id:str,body:EditorialReviewIn):
        with db.transaction() as c:
            result,script=snapshot(c,project_id)
            if result['blockers']:
                raise HTTPException(409,'Cannot accept with unresolved blockers: '+', '.join(result['blockers'])[:500])
            if body.final_export_id not in result['final_export_ids']:
                raise HTTPException(409,'Owner review must reference an existing final export')
            # Reuse the ORIGINAL M2.2 final-export fingerprint, not just its MP4 hash.
            # It fails closed if project revision, source evidence, narration, visuals,
            # rights assets, captions or owner approval changed since final render.
            from .youtube_private import resolve_export
            export,live_project,path=resolve_export(c,body.final_export_id)
            if export['project_id']!=project_id or live_project['project_id']!=project_id:
                raise HTTPException(409,'Final export belongs to another project')
            prior=db.one(c,'SELECT review_id FROM m26_editorial_reviews WHERE project_id=? AND final_export_id=? AND dependency_sha256=?',
                         (project_id,body.final_export_id,result['snapshot_sha256']))
            if prior:
                raise HTTPException(409,'This precise snapshot was already reviewed')
            rid=m.uid()
            c.execute('INSERT INTO m26_editorial_reviews(review_id,project_id,script_version_id,final_export_id,dependency_sha256,auditor,decision,notes,created_at) '
                      'VALUES (?,?,?,?,?,?,?,?,?)',(rid,project_id,script['script_version_id'],body.final_export_id,result['snapshot_sha256'],
                           body.auditor,'OWNER_REVIEWED_NOT_LEGALLY_CERTIFIED',body.notes,m.now()))
        return {'review_id':rid,'status':'OWNER_REVIEWED_NOT_LEGALLY_CERTIFIED',
                'independent_legal_clearance_certified':False,'auto_publish_enabled':False,
                'public_or_private_upload_performed':False}
