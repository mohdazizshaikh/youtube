import hashlib
import json
import shutil
import subprocess
from PIL import Image
import pytest
from pydantic import ValidationError
from app.domain_adapters import POLICIES
from app.domain_storyboards import Storyboard, render_board
from tools.domain_storyboard import demo_spec, build_one


@pytest.mark.parametrize('domain',sorted(POLICIES))
@pytest.mark.parametrize('fmt',['SHORT','LONG'])
def test_all_domain_format_drafts(tmp_path,domain,fmt):
    s=demo_spec(domain,fmt); p=tmp_path/'board.png'; r=render_board(s,p)
    assert r['board_sha256']==hashlib.sha256(p.read_bytes()).hexdigest()
    assert not r['publication_eligible'] and not r['claim_truth_verified']
    assert Image.open(p).size==((720,1280) if fmt=='SHORT' else (1280,720))
    with pytest.raises(FileExistsError):render_board(s,p)


@pytest.mark.parametrize('case',['unknown','duplicate','refutes','same_group','same_host','no_primary','missing_field','demo_url','non_ascii','no_locator','duplicate_url'])
def test_reject_bad_source_or_text(case):
    d=demo_spec('sports','SHORT').model_dump()
    if case=='unknown':d['claims'][0]['links'][1]['source_id']='X1'
    if case=='duplicate':d['claims'][0]['links'][1]['source_id']='S1'
    if case=='refutes':d['claims'][0]['links'][1]['relation']='REFUTES'
    if case=='same_group':d['sources'][1]['independence_group']=d['sources'][0]['independence_group']
    if case=='same_host':d['sources'][1]['url']='https://primary.invalid/other'
    if case=='no_primary':d['sources'][0]['record_type']='SECONDARY'
    if case=='missing_field':d['specialist_facts']={}
    if case=='demo_url':d['synthetic_demo']=False
    if case=='non_ascii':d['title']='नमस्ते Example'
    if case=='no_locator':d['claims'][0]['links'][0]['locator']='  '
    if case=='duplicate_url':d['sources'][1]['url']=d['sources'][0]['url']
    with pytest.raises(ValidationError):Storyboard.model_validate(d)


def test_manifest_and_input_binding(tmp_path):
    dest=tmp_path/'out'; r=build_one(demo_spec('science','LONG'),dest)
    assert json.loads((dest/'manifest.json').read_text())==r
    assert Storyboard.model_validate_json((dest/'input.json').read_text()).domain=='science'
    with pytest.raises(FileExistsError):build_one(demo_spec('science','LONG'),dest)


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='local FFmpeg unavailable')
def test_real_animatic(tmp_path):
    dest=tmp_path/'out'; r=build_one(demo_spec('sports','SHORT'),dest,True)
    assert r['animatic_sha256']==hashlib.sha256((dest/'animatic.mp4').read_bytes()).hexdigest()
    x=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(dest/'animatic.mp4')]))
    assert len(x['streams'])==1 and x['streams'][0]['codec_type']=='video'
    assert (x['streams'][0]['width'],x['streams'][0]['height'])==(720,1280)
    assert abs(float(x['format']['duration'])-3)<.1 and not r['accepted_video']
