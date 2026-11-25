import copy
import json
import shutil
import pytest
from tools import paired_mastered_pilot as p,bilingual_pilot as bp
from tools.domain_storyboard import demo_spec
from app.domain_storyboards import render_board
from test_phase15y import request as audio_request
from test_bilingual_compose import inputs,args,save
from test_narration_prepare import tone

PIN="a"*64


def request():
    return {"schema":p.REQUEST,"pair_sha256":PIN,"audio_request":audio_request()}


def check(obj):
    raw=p.json_bytes(obj)
    return p.validate(raw,p.sha(raw),PIN)


@pytest.mark.parametrize("field,value",[("schema","bad"),("pair_sha256","b"*64),
    ("pair_sha256",None),("audio_request",None),("audio_request",{}),("extra",1)])
def test_request(field,value):
    obj=request()
    obj[field]=value
    with pytest.raises(ValueError):check(obj)


def test_valid():
    obj,sub=check(request())
    assert obj==request() and p.pv.decode(sub)==obj["audio_request"]


def manifest():
    return {"fps":25,"duration_ms":4000,"frames":100,"scenes":[
        {"scene":1,"frames":50,"start_ms":0,"end_ms":2000},
        {"scene":2,"frames":50,"start_ms":2000,"end_ms":4000}]}


@pytest.mark.parametrize("field,value",[("fps",30),("duration_ms",4040),("frames",99),
    ("scenes",[]),("scenes",[{"scene":1}])])
def test_manifest(field,value):
    obj=manifest()
    obj[field]=value
    with pytest.raises(ValueError):p.check_schedule(obj,audio_request()["scenes"],4000)


@pytest.mark.parametrize("field,value",[("scene",2),("frames",49),("start_ms",40),("end_ms",1960)])
def test_scene(field,value):
    obj=manifest()
    obj["scenes"][0][field]=value
    with pytest.raises(ValueError):p.check_schedule(obj,audio_request()["scenes"],4000)


def test_schedule_valid():
    p.check_schedule(manifest(),audio_request()["scenes"],4000)


def test_default_renderer(tmp_path):
    board=demo_spec("technology","SHORT")
    board.specialist_facts[p.KEY]="1"
    with pytest.raises(ValueError,match="pinned parent renderer"):
        render_board(board,tmp_path/"board.png")


def test_incomplete(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="PAIR_INVENTORY"):p.verify(None,PIN,b"",PIN,tmp_path,PIN)


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),reason="local media required")
def test_real_mastered_pair(inputs,tmp_path):
    root,timing,caps,bundle=inputs
    for row in timing["scenes"]:
        for lang in p.LANGS:
            track=row[lang]
            raw=tone(seconds=2,frequency=270+row["scene"]+(40 if lang=="english" else 0),
                     amplitude=7000 if lang=="hindi" else 10000)
            (root/track["file"]).write_bytes(raw)
            track["sha256"]=bp.sha(raw)
    caps["timing_request_sha256"]=bp.sha(json.dumps(timing).encode())
    saved=save(inputs)
    board=demo_spec("technology","SHORT").model_dump()
    boards={"schema":bp.BOARD_SCHEMA,"bundle_manifest_sha256":saved["manifest_sha256"],
            "scenes":[{"scene":i,"hindi":copy.deepcopy(board),"english":copy.deepcopy(board),
                       "rights_attested":{"hindi":True,"english":True}} for i in (1,2)]}
    raw=bp.json_bytes(boards)
    pair=tmp_path/"master-parent"
    built=bp.build(*args(inputs),bundle,saved["manifest_sha256"],raw,bp.sha(raw),pair)
    obj=request()
    obj["pair_sha256"]=built["pair_sha256"]
    for lang in p.LANGS:
        obj["audio_request"]["tracks"][lang]["voice_sha256"]=p.sha(
            (pair/lang/"draft"/"narration.wav").read_bytes())
    raw=p.json_bytes(obj)
    common=(pair,built["pair_sha256"],raw,p.sha(raw))
    before={l:p.ps.inventory(pair/l) for l in p.LANGS}
    out=tmp_path/"mastered"
    result=p.build(*common,out)
    checked=p.verify(*common,out,result["mastered_pair_sha256"])
    assert checked["duration_ms"]==4000
    assert all(row=={"revision":0,"state":"PENDING"} for row in checked["review_states"].values())
    assert before=={l:p.ps.inventory(pair/l) for l in p.LANGS}
    for lang in p.LANGS:
        for i in (1,2):
            name=f"scene_{i:02}.png"
            assert (pair/lang/"draft"/name).read_bytes()==(out/lang/"draft"/name).read_bytes()
        assert result["runs"][lang]["decoded_16khz_audio"]["true_peak_dbtp"]<=-3
    with pytest.raises(ValueError):p.build(*common,out)
    from tools import workflow_pair_adapters as adapters
    parent_job={"input":{"run":pair.name,"pair_sha256":built["pair_sha256"]}}
    parent=adapters.audit(tmp_path,parent_job)
    assert parent["fresh_media_audit"] and not parent["original_input_recomposition_verified"]
    (tmp_path/"master-request").write_bytes(raw)
    job={"input":{"run":out.name,"request":"master-request","request_sha256":p.sha(raw),
                  "mastered_pair_sha256":result["mastered_pair_sha256"]}}
    audited=adapters.mastered(tmp_path,job,parent)
    assert audited["parent_bound_mastering_recomposition_verified"]
    assert audited["review_states"]==checked["review_states"]
    (out/"pair_dynamics.json").write_bytes(b"tamper")
    with pytest.raises(ValueError):adapters.mastered(tmp_path,job,parent)
    with pytest.raises(ValueError):p.verify(*common,out,result["mastered_pair_sha256"])
