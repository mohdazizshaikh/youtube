"""Human-supplied Hindi/English localization with immutable source linkage.

No translation provider, web lookup or voice generator is invoked here. A human
approval records a review, not truth, audio naturalness, translation accuracy,
or permission to publish. Existing scene/audio timelines are not mutated.
"""
from __future__ import annotations
from collections import Counter
import hashlib,json,re,unicodedata
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict
from . import db


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Pronunciation(Strict):
    written_term: str = Field(min_length=1,max_length=100)
    spoken_form: str = Field(min_length=1,max_length=200)
    note: str = Field(default='',max_length=400)

class LocaleVariantIn(Strict):
    locale: Literal['hi-IN','en-IN','en-US']
    localized_script: str = Field(min_length=25,max_length=15000)
    on_screen_text: list[str] = Field(min_length=1,max_length=40)
    pronunciation: list[Pronunciation] = Field(default_factory=list,max_length=200)
    method: Literal['OWNER_WRITTEN','EXTERNALLY_PREPARED_HUMAN_REVIEW_REQUIRED']
    numeric_conversion_explanation: str = Field(default='',max_length=1200)
    romanized_hinglish: bool = False

class LocaleReviewIn(Strict):
    reviewer: str = Field(min_length=2,max_length=100)
    owner_reviewed_entire_localized_script: Literal[True]
    owner_checked_names_numbers_units: Literal[True]
    owner_reviewed_visual_layout_typography: Literal[True]
    owner_checked_pronunciation_and_audio_plan: Literal[True]
    owner_reviewed_source_claims_and_disclosures: Literal[True]

NUMBER_RE=re.compile(r'\d+(?:[.,]\d+)*',re.UNICODE)
BIDI_CONTROLS={chr(x) for x in [0x202A,0x202B,0x202C,0x202D,0x202E,0x2066,0x2067,0x2068,0x2069]}


def numbers(text:str)->Counter:
    def normalize(digits):
        return ''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in digits)
    return Counter(normalize(n) for n in NUMBER_RE.findall(text))


def locale_audit(source:str, content:dict) -> dict:
    target=content['localized_script']
    flags=[]
    if any(x in target for x in BIDI_CONTROLS):flags.append('UNSAFE_DIRECTION_CONTROL_IN_SCRIPT')
    if any(any(x in t for x in BIDI_CONTROLS) for t in content['on_screen_text']):
        flags.append('UNSAFE_DIRECTION_CONTROL_IN_ON_SCREEN_TEXT')
    if any(not t.strip() or len(t)>450 for t in content['on_screen_text']):flags.append('INVALID_ON_SCREEN_TEXT')
    source_n=numbers(source);target_n=numbers(target)
    if source_n!=target_n:
        flags.append('NUMERIC_CONTENT_CHANGED_REQUIRES_DOCUMENTED_REVIEW')
    if content['locale']=='hi-IN':
        has_devanagari=any('\u0900'<=x<='\u097f' for x in target+' '.join(content['on_screen_text']))
        if not has_devanagari and not content.get('romanized_hinglish'):
            flags.append('HINDI_SCRIPT_MISSING_AND_NOT_MARKED_HINGLISH')
    return {'flags':flags,'source_numbers':dict(source_n),'target_numbers':dict(target_n),
            'scene_text_count':len(content['on_screen_text']),
            'automatic_translation_performed':False,'source_claim_truth_verified':False,
            'voice_naturalness_verified':False,'human_visual_and_audio_review_required':True}


def dependencies(c,project_id,script):
    # A change in reviewed claim/evidence metadata invalidates locale approval.
    claims=db.many(c,'SELECT cl.claim_id,cl.verification_status,cl.updated_at '
        'FROM script_claim_links sl JOIN claims cl ON sl.claim_id=cl.claim_id '
        'WHERE sl.script_version_id=? ORDER BY cl.claim_id',(script['script_version_id'],))
    sources=db.many(c,'SELECT source_version_id FROM m1_project_sources WHERE project_id=? ORDER BY source_version_id',(project_id,))
    evidence=db.many(c,'SELECT e.claim_id,e.source_version_id,e.relation,e.locator '
        'FROM evidence_edges e WHERE e.claim_id IN (SELECT claim_id FROM script_claim_links WHERE script_version_id=?) '
        'ORDER BY e.claim_id,e.source_version_id,e.locator',(script['script_version_id'],))
    value=json.dumps({'script_id':script['script_version_id'],'script_sha':script['content_sha256'],
         'claims':claims,'bound_sources':sources,'evidence':evidence},ensure_ascii=False,sort_keys=True)
    return hashlib.sha256(value.encode('utf8')).hexdigest()


def register_localization(app):
    from . import main as m

    @app.get('/api/m25/capabilities')
    def locale_caps():
        return {'owner_authored_localized_script':True,'reviewed_pronunciation_glossary':True,
                'static_on_screen_text_metadata':True,'translation_model_bundled':False,
                'auto_translate':False,'auto_dub_or_retime':False,
                'independent_translation_quality_verified':False,
                'supported_locales':['hi-IN','en-IN','en-US'],
                'status':'HUMAN_PREPARED_LOCALE_VARIANTS_ONLY'}

    @app.post('/api/projects/{project_id}/m25/localizations')
    def create_variant(project_id:str,body:LocaleVariantIn):
        with db.transaction() as c:
            m.from_project(c,project_id)
            script=m.latest_script(c,project_id)
            if not script:raise HTTPException(409,'Original script must exist')
            if body.locale==script['original_language']:
                raise HTTPException(422,'Localizations must target a DIFFERENT locale')
            doc=body.model_dump(mode='json')
            audit=locale_audit(script['script_text'],doc)
            hard=[x for x in audit['flags'] if x.startswith(('UNSAFE_','INVALID_','HINDI_SCRIPT_MISSING'))]
            if hard:raise HTTPException(422,{'blockers':hard})
            if 'NUMERIC_CONTENT_CHANGED_REQUIRES_DOCUMENTED_REVIEW' in audit['flags'] and not body.numeric_conversion_explanation.strip():
                raise HTTPException(422,'Changed numbers require specific, documented human conversion explanation')
            existing=db.one(c,'SELECT variant_id FROM m25_localized_variants WHERE project_id=? AND script_version_id=? AND locale=?',
                            (project_id,script['script_version_id'],body.locale))
            if existing:raise HTTPException(409,'Locale variant immutable: create a new script revision')
            digest=hashlib.sha256(m.j(doc).encode('utf8')).hexdigest();d=dependencies(c,project_id,script)
            vid=m.uid()
            c.execute('INSERT INTO m25_localized_variants (variant_id,project_id,script_version_id,source_script_sha256,dependency_sha256,locale,content_json,content_sha256,status,created_at) '
                      'VALUES (?,?,?,?,?,?,?,?,?,?)',(vid,project_id,script['script_version_id'],script['content_sha256'],d,body.locale,m.j(doc),digest,'PENDING_OWNER_REVIEW',m.now()))
        return {'variant_id':vid,'status':'PENDING_OWNER_REVIEW','audit':audit,
                'render_scene_audio_modified':False,'publication_eligible':False}

    @app.get('/api/projects/{project_id}/m25/localizations/{variant_id}')
    def get_variant(project_id:str,variant_id:str):
        with db.read() as c:
            m.from_project(c,project_id)
            record=db.one(c,'SELECT * FROM m25_localized_variants WHERE project_id=? AND variant_id=?',(project_id,variant_id))
            if not record:raise HTTPException(404,'Locale draft not found')
            script=m.latest_script(c,project_id)
            stale=(not script or script['script_version_id']!=record['script_version_id'] or
                   script['content_sha256']!=record['source_script_sha256'] or
                   dependencies(c,project_id,script)!=record['dependency_sha256'])
        return {'variant_id':variant_id,'locale':record['locale'],'status':'STALE' if stale else record['status'],
                'source_script_sha256':record['source_script_sha256'],
                'data':json.loads(record['content_json']),
                'requires_re_review':stale or record['status']!='OWNER_REVIEWED',
                'voice_audio_generated':False,'publication_eligible':False}

    @app.post('/api/projects/{project_id}/m25/localizations/{variant_id}/owner-review')
    def approve_variant(project_id:str,variant_id:str,body:LocaleReviewIn):
        with db.transaction() as c:
            m.from_project(c,project_id)
            record=db.one(c,'SELECT * FROM m25_localized_variants WHERE project_id=? AND variant_id=?',(project_id,variant_id))
            if not record:raise HTTPException(404,'Locale draft not found')
            if record['status']!='PENDING_OWNER_REVIEW':raise HTTPException(409,'Already reviewed')
            script=m.latest_script(c,project_id)
            if not script or script['script_version_id']!=record['script_version_id'] or script['content_sha256']!=record['source_script_sha256'] or dependencies(c,project_id,script)!=record['dependency_sha256']:
                raise HTTPException(409,'Source script or evidence changed: localized variant is stale')
            content=json.loads(record['content_json']);audit=locale_audit(script['script_text'],content)
            if any(k.startswith(('UNSAFE_','INVALID_','HINDI_SCRIPT_MISSING')) for k in audit['flags']):
                raise HTTPException(409,'Unsafe localized content')
            if 'NUMERIC_CONTENT_CHANGED_REQUIRES_DOCUMENTED_REVIEW' in audit['flags'] and not content['numeric_conversion_explanation'].strip():
                raise HTTPException(409,'Number change not explained')
            c.execute('UPDATE m25_localized_variants SET status=?,reviewer=?,reviewed_at=? WHERE variant_id=?',
                      ('OWNER_REVIEWED',body.reviewer,m.now(),variant_id))
        return {'variant_id':variant_id,'status':'OWNER_REVIEWED','human_attestation_only':True,
                'audio_generated':False,'scene_retiming_completed':False,'publish_ready':False}
