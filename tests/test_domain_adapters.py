"""Executable, differentiated domain metadata checks (NOT AI expertise claims)."""
import pytest
from fastapi.testclient import TestClient
from app.domain_adapters import POLICIES, DomainEvidenceIn, evaluate
from app.main import app

@pytest.mark.parametrize('domain',sorted(POLICIES))
def test_each_domain_requires_different_fields_and_visual_grammar(domain):
    fields=POLICIES[domain].specialist_fields
    assert len(fields)==3
    assert len(set(fields))==3
    inputs={'title':'Human-supplied original evidence review', 'claims':['Example claim'],
            'sources':[{'url':'https://a.example/data','publisher':'Primary source', 'independence_group':'official', 'record_type':'PRIMARY','observed_at_utc':'2026-11-24T00:00:00Z'},
                       {'url':'https://b.example/analysis','publisher':'Independent publisher','independence_group':'independent','record_type':'SECONDARY','observed_at_utc':'2026-11-24T00:00:00Z'}],
            'specialist_facts':dict.fromkeys(fields,'human reviewed fact'),
            'visual_license_reviewed':True,'sensitive_claims_reviewed':True}
    result=evaluate(domain,DomainEvidenceIn(**inputs))
    assert result['blockers']==[]
    assert result['publication_eligible'] is False
    assert result['claim_truth_verified'] is False
    assert result['status']=='METADATA_COMPLETE_HUMAN_FACT_CHECK_REQUIRED'
    missing=evaluate(domain,DomainEvidenceIn(**{**inputs,'specialist_facts':{}}))
    assert 'DOMAIN_FIELDS_MISSING' in missing['blockers']
    assert set(missing['missing_specialist_fields'])==set(fields)


def test_unique_specialist_contracts_and_review_api():
    assert len(POLICIES)==12
    assert len({p.specialist_fields for p in POLICIES.values()})==12
    assert len({p.visual_grammar for p in POLICIES.values()})==12
    with TestClient(app) as c:
        assert c.get('/api/domain-adapters').json()['count']==12
        assert c.post('/api/domain-adapters/unknown/review-evidence',json={'title':'unknown domain','claims':['a'],'sources':[]}).status_code==404


def test_source_groups_do_not_infer_real_independence():
    payload=DomainEvidenceIn(title='Contextual sports analysis',claims=['Unverified claim'],sources=[
        {'url':'http://insecure.example/p','publisher':'Publisher','independence_group':'same', 'record_type':'COMMUNITY','observed_at_utc':'unknown-date'}],specialist_facts={'sport':'cricket'})
    result=evaluate('sports',payload)
    assert 'INSUFFICIENT_DECLARED_INDEPENDENT_SOURCES' in result['blockers']
    assert 'PRIMARY_SOURCE_MISSING' in result['blockers']
    assert 'NON_HTTPS_SOURCE_NEEDS_MANUAL_REVIEW' in result['blockers']
