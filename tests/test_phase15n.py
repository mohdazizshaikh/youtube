import io
import json
import pytest
from PIL import Image,ImageDraw
from tools import native_flow_motion as m,mixed_review_transaction as t
from tools import bilingual_review_transaction as tx

PIN="a"*64
REQ="b"*64


def motion_req():
    return {"schema":m.REQUEST,"native_sha256":PIN,"effect":"STEP_HIGHLIGHT_V1"}


@pytest.mark.parametrize("key,value",[("schema","bad"),("native_sha256","0"*64),
    ("native_sha256",None),("effect","OTHER"),("effect",True),("extra",1)])
def test_motion_request(key,value):
    obj=motion_req()
    obj[key]=value
    raw=m.json_bytes(obj)
    with pytest.raises(ValueError):m.validate(raw,m.sha(raw),PIN)


@pytest.mark.parametrize("frames",[15,16,17,18,25,26,749,750])
def test_stages(frames):
    out=m.stages(frames)
    assert len(out)==3 and sum(out)==frames and min(out)>=5 and max(out)-min(out)<=1


@pytest.mark.parametrize("frames",[0,14,751,True,15.0,"15",None])
def test_invalid_frames(frames):
    with pytest.raises(ValueError):m.stages(frames)


def board(fmt):
    size=(720,1280) if fmt=="SHORT" else (1280,720)
    img=Image.new("RGB",size,"#101e31")
    draw=ImageDraw.Draw(img)
    boxes=([(84,240+i*290,636,440+i*290) for i in range(3)] if fmt=="SHORT" else
           [(48+i*408,250,416+i*408,500) for i in range(3)])
    for box in boxes:draw.rounded_rectangle(box,radius=22,fill="#20374d",outline="#74d9c6",width=3)
    out=io.BytesIO()
    img.save(out,format="PNG")
    return out.getvalue()


def low(png):
    with Image.open(io.BytesIO(png)) as img:
        return img.convert("RGB").resize((m.SIZE,m.SIZE),Image.Resampling.BILINEAR).tobytes()


@pytest.mark.parametrize("fmt",["SHORT","LONG"])
def test_frames(fmt):
    images=m.images(board(fmt),fmt)
    assert len(set(images))==3
    row=list(zip([5,5,5],images))
    data=b"".join(low(png)*n for n,png in row)
    assert m.frame_check(data,[row])["frames_compared"]==15
    with pytest.raises(ValueError,match="MOTION_DECODE_COUNT"):m.frame_check(data[:-1],[row])
    with pytest.raises(ValueError,match="MOTION_FRAME_MISMATCH"):
        m.frame_check(low(images[1])+data[m.BYTES:],[row])


def mixed_req():
    return {"schema":t.REQUEST,"pair_mix_sha256":PIN,
            "reviews":{l:{"revision":0,"review":{}} for l in tx.LANGS}}


@pytest.mark.parametrize("field,value",[("schema","bad"),("pair_mix_sha256","0"*64),
    ("pair_mix_sha256",None),("reviews",None),("reviews",[]),("reviews",{}),("extra",1)])
def test_mixed_req(field,value):
    obj=mixed_req()
    obj[field]=value
    raw=m.json_bytes(obj)
    with pytest.raises(ValueError):t.validate(raw,m.sha(raw),PIN)


@pytest.mark.parametrize("value",[-1,True,0.0,100000,"0",None])
def test_mixed_revision(value):
    obj=mixed_req()
    obj["reviews"]["hindi"]["revision"]=value
    raw=m.json_bytes(obj)
    with pytest.raises(ValueError):t.validate(raw,m.sha(raw),PIN)


def plan():
    return {"schema":t.SCHEMA,"request_sha256":REQ,"pair_mix_sha256":PIN,
            "native_sha256":None,"publication_eligible":False,"languages":{
        l:{"manifest_sha256":"c"*64,"expected_revision":0,"review_sha256":"d"*64,
           "proposed_state":"DEMO_BLOCKED","blocker_count":1,"history_sha256":tx.pv.canonical([])}
        for l in tx.LANGS}}


def test_schema_separation():
    raw=m.json_bytes(plan())
    assert t.checked_plan(raw,m.sha(raw),REQ,PIN)==plan()
    with pytest.raises(ValueError):tx.validate_plan(raw,m.sha(raw),REQ,PIN,None)


@pytest.mark.parametrize("field,value",[("schema",tx.SCHEMA),("pair_mix_sha256","0"*64),
    ("native_sha256","c"*64),("request_sha256","0"*64),("publication_eligible",True),("extra",1)])
def test_mixed_plan(field,value):
    obj=plan()
    obj[field]=value
    raw=m.json_bytes(obj)
    with pytest.raises(ValueError):t.checked_plan(raw,m.sha(raw),REQ,PIN)
