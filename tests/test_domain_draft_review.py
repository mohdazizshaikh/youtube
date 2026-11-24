import copy
import shutil
import pytest
from app.domain_draft_review import review_packet, template, evaluate, CHECKS
from app.domain_draft_video import DraftPlan, compose, digest
from test_domain_draft_video import sample

pytestmark=pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='local FFmpeg required')

@pytest.fixture(scope='module')
def media(tmp_path_factory):
    root=tmp_path_factory.mktemp('review'); assets=root/'assets';assets.mkdir()
    plan=DraftPlan.model_validate(sample(assets));draft=root/'draft'
    compose(plan,assets,draft)
    pin=digest((draft/'manifest.json').read_bytes())
    return draft,assets,pin,review_packet(draft,assets,pin)


def ready(packet):
    r=template(packet);r['reviewer']='Fixture reviewer'
    for s in r['scenes']:s['checks']=dict.fromkeys(CHECKS,'PASS')
    return r


def test_packet_scene_context(media):
    d,a,p,packet=media
    assert packet['technical_audit_passed'] and not packet['publication_eligible']
    assert len(packet['scenes'])==2 and packet['scenes'][0]['claims'] and packet['scenes'][0]['sources']
    assert template(packet)['scenes'][0]['checks']['asset_rights']=='NOT_REVIEWED'


def test_incomplete_review(media):
    d,a,p,packet=media
    r=evaluate(d,a,p,template(packet))
    assert not r['self_attested_editorial_checklist_complete'] and len(r['blockers'])==14


def test_synthetic_all_pass_still_blocked(media):
    d,a,p,packet=media
    r=evaluate(d,a,p,ready(packet))
    assert r['blockers']==[{'reason':'SYNTHETIC_DEMO_NOT_ELIGIBLE'}]
    assert not r['publication_eligible'] and not r['reviewer_identity_verified']
    assert 'reviewer' not in r and 'notes' not in r


@pytest.mark.parametrize('case',['packet','scene','duplicate','missing','boolean','missing_check','revision_note','extra','pin'])
def test_bad_review(media,case):
    d,a,p,packet=media;r=ready(packet)
    if case=='packet':r['packet_sha256']='0'*64
    if case=='scene':r['scenes'][0]['scene_sha256']='0'*64
    if case=='duplicate':r['scenes'][1]=copy.deepcopy(r['scenes'][0])
    if case=='missing':r['scenes'].pop()
    if case=='boolean':r['scenes'][0]['checks']['asset_rights']=True
    if case=='missing_check':del r['scenes'][0]['checks']['asset_rights']
    if case=='revision_note':r['scenes'][0]['checks']['asset_rights']='REVISE'
    if case=='extra':r['publication_eligible']=True
    if case=='pin':r['manifest_sha256']='0'*64
    with pytest.raises(ValueError):evaluate(d,a,p,r)


def test_changed_media_blocks_even_with_old_review(media,tmp_path):
    d,a,p,packet=media
    out=tmp_path/'draft';shutil.copytree(d,out)
    (out/'captions.vtt').write_text('tampered',encoding='utf8')
    with pytest.raises(ValueError,match='file hash mismatch'):evaluate(out,a,p,ready(packet))


def test_explicit_revision_is_reported(media):
    d,a,p,packet=media;r=ready(packet)
    r['scenes'][1]['checks']['visual_accuracy']='REVISE';r['scenes'][1]['notes']='Correct illustration before re-review.'
    out=evaluate(d,a,p,r)
    assert {'scene':2,'check':'visual_accuracy','reason':'REVISE'} in out['blockers']
    assert 'Correct illustration' not in str(out)
