import pytest
from fastapi.testclient import TestClient
from app.editorial_evidence import calculate
import app.main as main


def fixture():
    project={'project_id':'p1','revision':1}
    script={'script_version_id':'s1','content_sha256':'a'*64}
    claims=[{'claim_id':'c1','verification_status':'SUPPORTED','updated_at':'time'}]
    links=[{'claim_id':'c1','span_start':0,'span_end':20}]
    evidence=[{'claim_id':'c1','relation':'SUPPORTS','source_version_id':'src','locator':'A1'}]
    media=[{'asset_id':'a','rights_attested':1,'license_note':'Rights reviewed separately','content_sha256':'b'*64}]
    final=[{'export_id':'ex','status':'OWNER_APPROVED_FINAL_EXPORT','file_sha256':'c'*64}]
    return project,script,claims,links,evidence,media,final,[]


def test_editorial_audit_uses_dependency_fingerprint_and_requires_human_review():
    a=fixture();one=calculate(*a)
    assert one['blockers']==[]
    assert one['status']=='METADATA_PRESENT_INDEPENDENT_OWNER_REVIEW_REQUIRED'
    assert not one['publication_eligible'] and not one['copyright_legality_certified']
    assert one['snapshot_sha256']==calculate(*a)['snapshot_sha256']
    b=fixture();b[2][0]['verification_status']='REFUTED'
    changed=calculate(*b)
    assert 'CLAIM_NOT_SUPPORTED:c1' in changed['blockers']
    assert changed['snapshot_sha256']!=one['snapshot_sha256']


def test_missing_support_rights_and_final_are_rejected():
    p,s,c,l,e,m,f,o=fixture()
    e.clear();m[0]['rights_attested']=0
    result=calculate(p,s,c,l,e,m,[],o)
    assert 'CLAIM_SUPPORTING_EVIDENCE_MISSING:c1' in result['blockers']
    assert 'MEDIA_RIGHTS_RECORD_INCOMPLETE:a' in result['blockers']
    assert 'OWNER_APPROVED_FINAL_VIDEO_MISSING' in result['blockers']


def test_editorial_api_never_marks_publication_eligible(tmp_path,monkeypatch):
    monkeypatch.setenv('VIRALOS_DB',str(tmp_path/'audit.db'))
    monkeypatch.setattr(main,'OUT',tmp_path/'outs')
    with TestClient(main.app) as c:
        ch=c.post('/api/channels',json={'name':'Audit cricket','sport_id':'cricket','locale':'en-US','market':'USA','timezone':'America/New_York'}).json()
        pr=c.post('/api/projects',json={'channel_id':ch['channel_id'],'title':'Evidence-backed cricket diagrams','original_angle':'Original animation footage to explain fielding patterns.'}).json()
        result=c.get(f'/api/projects/{pr["project_id"]}/m26/editorial-audit')
        assert result.status_code==200
        assert result.json()['status']=='BLOCKED'
        assert 'SCRIPT_MISSING' in result.json()['blockers']
        assert 'OWNER_APPROVED_FINAL_VIDEO_MISSING' in result.json()['blockers']
        data={'final_export_id':'fake','auditor':'Owner','notes':'I have independently reviewed the footage and audio.',
              'checked_full_final_video':True,'checked_every_material_claim_and_original_source':True,
              'independently_checked_asset_and_music_rights':True,
              'reviewed_originality_and_transformative_value':True,'reviewed_ai_disclosure_and_sensitive_subjects':True}
        assert c.post(f'/api/projects/{pr["project_id"]}/m26/editorial-owner-review',json=data).status_code==409
        assert c.post(f'/api/projects/{pr["project_id"]}/m26/editorial-owner-review',json={**data,'checked_full_final_video':False}).status_code==422
