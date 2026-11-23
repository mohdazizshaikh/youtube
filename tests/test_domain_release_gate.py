import hashlib
import json
import pytest
from tools.domain_release_gate import evaluate, matrix_template


def test_12_domain_24_format_manifest_defaults_all_pending(tmp_path):
    template=matrix_template()
    assert len(template['records'])==24
    assert len({(x['domain'],x['format']) for x in template['records']})==24
    result=evaluate(template,tmp_path)
    assert result['checks_complete']==0
    assert not result['twelve_fully_operational_ai_domains_proven']
    assert not result['public_publishing_allowed']


def test_domain_manifest_rejects_duplicate_and_wrong_schema(tmp_path):
    template=matrix_template()
    template['records'][0]=dict(template['records'][1])
    with pytest.raises(ValueError):evaluate(template,tmp_path)
    with pytest.raises(ValueError):evaluate({'schema':'wrong','records':[]},tmp_path)


def test_real_file_hash_and_human_attestation_still_not_legal_certification(tmp_path):
    manifest=matrix_template()
    video=tmp_path/'clip.mp4';video.write_bytes(b'only a unit test fixture not an accepted video')
    claims=tmp_path/'claims.json';claims.write_text('{"fixture":true}')
    rights=tmp_path/'rights.json';rights.write_text('{"fixture":true}')
    record=manifest['records'][0]
    for kind,file in [('video',video),('claims_manifest',claims),('rights_manifest',rights)]:
        record[f'{kind}_path']=file.name
        record[f'{kind}_sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
    for flag in ('domain_expert_checked_sources','owner_checked_full_video','owner_checked_originality',
                 'owner_checked_music_footage_rights','owner_checked_on_screen_disclosures',
                 'locale_checked_by_native_speaker'):
        record[flag]=True
    record['domain_expert']='Synthetic test expert'
    record['review_notes']='Synthetic test assertion, no real human approval exists.'
    result=evaluate(manifest,tmp_path)
    assert result['checks_complete']==1
    assert not result['facts_independently_verified_by_tool']
    assert not result['media_licensing_legally_certified']
    video.write_bytes(b'modified')
    assert 'video_path:ARTIFACT_HASH_MISMATCH' in evaluate(manifest,tmp_path)['individual_results'][0]['blockers']
