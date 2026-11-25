import io
import pytest
from PIL import Image,ImageDraw,ImageChops
from tools import chart_scene_transition as t

PIN="a"*64


def request():
    return {"schema":t.REQUEST,"chart_pair_sha256":PIN,"effect":t.EFFECT,"fade_frames":5}


@pytest.mark.parametrize("field,value",[("schema","bad"),("chart_pair_sha256","bad"),
    ("chart_pair_sha256",None),("effect","CROSSFADE"),("fade_frames",2),("fade_frames",9),
    ("fade_frames",True),("fade_frames",5.0),("fade_frames","5"),("extra",1)])
def test_request(field,value):
    obj=request()
    obj[field]=value
    raw=t.json_bytes(obj)
    with pytest.raises(ValueError):t.validate(raw,t.sha(raw),PIN)


@pytest.mark.parametrize("fade",[3,5,8])
@pytest.mark.parametrize("index",[0,1,2])
def test_schedule(index,fade):
    rows=t.schedule(40,index,3,fade)
    assert sum(n for n,a in rows)==40
    assert len([a for n,a in rows if a==0])==1
    assert [n for n,a in rows if a==0][0]>=13
    assert [a for n,a in rows if a>0]==(list(range(fade,0,-1)) if index else [])+(
        list(range(1,fade+1)) if index<2 else [])


@pytest.mark.parametrize("args",[(12,0,2,3),(25,1,3,8),(40,-1,3,3),(40,3,3,3),
    (40,0,1,3),(40,0,9,3),(40,True,3,3),(40,0,3,True),(751,0,2,3)])
def test_schedule_invalid(args):
    with pytest.raises(ValueError):t.schedule(*args)


def png(im):
    b=io.BytesIO()
    im.save(b,format="PNG")
    return b.getvalue()


@pytest.mark.parametrize("fmt",["SHORT","LONG"])
@pytest.mark.parametrize("fade",[3,5,8])
def test_frames(fmt,fade):
    w,h=(720,1280) if fmt=="SHORT" else (1280,720)
    im=Image.new("RGB",(w,h),"#101e31")
    draw=ImageDraw.Draw(im)
    draw.rectangle((50,80,w-50,h-130),fill="#74d9c6")
    draw.rectangle((0,h-104,w,h),fill="#5f2a35")
    raw=png(im)
    assert t.image(raw,fmt,0,fade)==raw
    rows=[]
    for n,a in t.schedule(40,1,3,fade):
        stage=t.image(raw,fmt,a,fade)
        with Image.open(io.BytesIO(stage)) as s:
            assert ImageChops.difference(im.crop((0,h-104,w,h)),s.crop((0,h-104,w,h))).getbbox() is None
        rows.append((n,stage))
    def low(data):
        with Image.open(io.BytesIO(data)) as s:
            return s.convert("RGB").resize((t.motion.SIZE,t.motion.SIZE),Image.Resampling.BILINEAR).tobytes()
    data=b"".join(low(p)*n for n,p in rows)
    assert t.frame_check(data,[rows])["frames_compared"]==40
    with pytest.raises(ValueError,match="TRANSITION_FRAME_COUNT"):t.frame_check(data[:-1],[rows])
    with pytest.raises(ValueError,match="TRANSITION_FRAME_MISMATCH"):
        t.frame_check(low(raw)+data[t.motion.BYTES:],[rows])


def pts(count=25):
    return {"streams":[{"time_base":"1/12800"}],"frames":[{"pts":i*512} for i in range(count)]}


def test_pts():
    assert t.check_pts(pts(),25)["presentation_timestamps_verified"]


@pytest.mark.parametrize("value",[None,False,512.0,511,513,-1,0,"512"])
def test_pts_grid(value):
    obj=pts()
    obj["frames"][1]["pts"]=value
    with pytest.raises(ValueError,match="PTS_GRID"):t.check_pts(obj,25)


@pytest.mark.parametrize("value",[None,"0/1","1/0","-1/12800","bad","1/1000"])
def test_pts_base(value):
    obj=pts()
    obj["streams"][0]["time_base"]=value
    with pytest.raises(ValueError):t.check_pts(obj,25)


@pytest.mark.parametrize("count",[0,24,26,1501,True])
def test_pts_count(count):
    with pytest.raises(ValueError):t.check_pts(pts(),count)


def test_incomplete(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="TRANSITION_INVENTORY"):t.verify((),None,PIN,b"",PIN,tmp_path,PIN)
