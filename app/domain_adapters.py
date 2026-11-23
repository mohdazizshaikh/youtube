"""Twelve *bounded* domain research adapters — executable checklists, not 144 AI agents.

This validates evidence metadata and specialist facts supplied by a human. It never
fetches a webpage, verifies a factual assertion, generates a video or declares a
project fit for publication. Domain policies are deliberately different.
"""
from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urlsplit
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict


@dataclass(frozen=True)
class Policy:
    specialist_fields: tuple[str,...]
    reason: str
    visual_grammar: str
    minimum_groups: int = 2
    explicit_warning: str = 'HUMAN_DOMAIN_EDITOR_REQUIRED'


POLICIES: dict[str, Policy] = {
    'newsroom': Policy(('original_statement_url','event_timestamp_utc','right_of_reply_status'),
                       'Separate eyewitness/official records and allow response', 'source-dated chronological evidence board'),
    'science': Policy(('study_identifier','methods_summary','sample_size_or_not_applicable'),
                      'Methods, evidence strength, sample size and replication', 'uncertainty-labelled study diagram'),
    'technology': Policy(('product_version','reproduction_steps','tested_environment'),
                         'Observed test results must be reproducible and versioned', 'screen capture plus observed-vs-claimed callouts'),
    'business': Policy(('filing_or_primary_record','reporting_period','currency_and_units'),
                       'Arithmetical claims need original filing and specified currency', 'auditable financial chart with time axis'),
    'gaming': Policy(('game_version','gameplay_provenance','publisher_footage_rights'),
                     'Gameplay authenticity, patch identity and publisher rights', 'original gameplay capture with annotation'),
    'history': Policy(('primary_archive_identifier','date_basis','translation_uncertainty'),
                      'Archive provenance, chronology and disputed translations', 'dated map and archive quotation with attribution'),
    'space': Policy(('mission_or_instrument','agency_source','physical_units'),
                    'Observational versus simulated material and units', 'scale-labelled, simulation-disclosed mission timeline'),
    'learning': Policy(('learning_objective','misconception','check_for_understanding'),
                       'Demonstrable learner outcome and misconception correction', 'worked example followed by retrieval check'),
    'sports': Policy(('sport','fixture_identifier','statistic_provenance'),
                     'Score, roster and tactic validity; broadcast rights separate', 'original playing-field tactical animation'),
    'career': Policy(('country_or_region','evidence_period','qualification_or_skill'),
                     'Labor market evidence is geography/date bound', 'location/date-labelled career decision tree'),
    'productivity': Policy(('baseline_measurement','measurement_window','workflow_reproduction'),
                           'Measure improvements, report confounders and reproducibility', 'before-after process flow with baseline'),
    'culture': Policy(('original_creator_attribution','trend_origin_date','rumor_review_status'),
                      'Avoid laundering rumors or appropriating creator media', 'attributed timeline with rumor/disputed labels'),
}

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class ExternalSource(Strict):
    url: str = Field(min_length=12,max_length=2000)
    publisher: str = Field(min_length=2,max_length=160)
    independence_group: str = Field(min_length=2,max_length=160)
    record_type: Literal['PRIMARY','SECONDARY','COMMUNITY','OWNER_OBSERVATION']
    observed_at_utc: str = Field(min_length=10,max_length=40)

class DomainEvidenceIn(Strict):
    title: str = Field(min_length=8,max_length=240)
    claims: list[str] = Field(min_length=1,max_length=40)
    sources: list[ExternalSource] = Field(max_length=50)
    specialist_facts: dict[str,str] = Field(default_factory=dict)
    visual_license_reviewed: bool = False
    sensitive_claims_reviewed: bool = False


def evaluate(domain: str, evidence: DomainEvidenceIn) -> dict:
    if domain not in POLICIES:
        raise ValueError('Unknown domain')
    policy=POLICIES[domain]
    missing=[field for field in policy.specialist_fields
             if not isinstance(evidence.specialist_facts.get(field),str)
             or not evidence.specialist_facts[field].strip()]
    errors=[]
    if missing:
        errors.append('DOMAIN_FIELDS_MISSING')
    sources=evidence.sources
    if any(urlsplit(x.url).scheme.lower()!='https' or not urlsplit(x.url).netloc for x in sources):
        errors.append('NON_HTTPS_SOURCE_NEEDS_MANUAL_REVIEW')
    groups={x.independence_group.strip().casefold() for x in sources}
    if len(groups)<policy.minimum_groups:
        errors.append('INSUFFICIENT_DECLARED_INDEPENDENT_SOURCES')
    if not any(x.record_type=='PRIMARY' for x in sources):
        errors.append('PRIMARY_SOURCE_MISSING')
    if len(evidence.claims)>len(sources):
        errors.append('CLAIMS_REQUIRE_INDIVIDUAL_SOURCE_LINKING')
    if not evidence.visual_license_reviewed:
        errors.append('VISUAL_LICENSE_REVIEW_PENDING')
    if not evidence.sensitive_claims_reviewed:
        errors.append('SENSITIVE_CLAIM_REVIEW_PENDING')
    return {
        'domain':domain,'status':'BLOCKED_METADATA_REVIEW' if errors else 'METADATA_COMPLETE_HUMAN_FACT_CHECK_REQUIRED',
        'required_specialist_fields':list(policy.specialist_fields),
        'missing_specialist_fields':missing,'declared_independence_groups':len(groups),
        'declared_sources':len(sources),'claim_count':len(evidence.claims),
        'blockers':errors,'research_rationale':policy.reason,'visual_grammar':policy.visual_grammar,
        'external_webpages_fetched':False,'claim_truth_verified':False,
        'copyright_clearance_certified':False,'owner_editor_approval_required':True,
        'publication_eligible':False,
    }


def register_domain_adapters(app):
    @app.get('/api/domain-adapters')
    def list_adapters():
        return {'domains':{k:{'specialist_fields':list(v.specialist_fields),
                     'visual_grammar':v.visual_grammar,'rationale':v.reason,
                     'status':'IMPLEMENTED_METADATA_GATES_ONLY_NOT_FULL_CREATIVE_OS'}
                      for k,v in POLICIES.items()},'count':len(POLICIES),
                'actual_specialist_AI_engines_proven':0}

    @app.post('/api/domain-adapters/{domain}/review-evidence')
    def check_domain(domain:str, evidence:DomainEvidenceIn):
        if domain not in POLICIES:
            raise HTTPException(404,'Domain not available')
        return evaluate(domain,evidence)
