import io
import pytest
from PIL import Image,ImageDraw,ImageChops
from tools import chart_pair_motion as m

PIN="a"*64


def request():
    return {"schema":m.REQUEST,"chart_pair_sha256":PIN,"effect":"VALUE_ROW_HIGHLIGHT_V1"}


@pytest.mark.parametrize("key,value",[("schema","bad"),("chart_pair_sha256","0"*64),
    ("chart_pair_sha256",None),("effect","GROW_BARS"),("effect",True),("extra",1)])
def test_request(key,value):
    obj=request()
    obj[key]=value
    raw=m.json_bytes(obj)
    with pytest.raises(ValueError):m.validate(raw,m.sha(raw),PIN)


def test_valid_request():
    raw=m.json_bytes(request())
    assert m.validate(raw,m.sha(raw),PIN)==request()


@pytest.mark.parametrize("count",[3,4,5])
@pytest.mark.parametrize("frames",[25,26,51,750])
def test_frames(count,frames):
    out=m.stages(frames,count)
    assert len(out)==count and sum(out)==frames and min(out)>=5 and max(out)-min(out)<=1


@pytest.mark.parametrize("frames,count",[(14,3),(19,4),(24,5),(751,3),(True,3),(25,True),
    (25,2),(25,6),(25,3.0),(25.0,3),(None,3)])
def test_invalid_frames(frames,count):
    with pytest.raises(ValueError):m.stages(frames,count)


def png(im):
    buf=io.BytesIO()
    im.save(buf,format="PNG")
    return buf.getvalue()


def synthetic(fmt,count):
    dims=(720,1280) if fmt=="SHORT" else (1280,720)
    img=Image.new("RGB",dims,"#101e31")
    draw=ImageDraw.Draw(img)
    for i,(a,b,c,d) in enumerate(m.row_boxes(fmt,count)):
        draw.rounded_rectangle((a,b,c-1,d-1),radius=9,fill=m.BACKGROUND)
        draw.rectangle((a+60,b+8,a+110,b+22),fill="white")
        draw.ellipse((a+12,b+8,a+28,b+24),fill="#74d9c6")
    return img


def low(raw):
    with Image.open(io.BytesIO(raw)) as im:
        return im.convert("RGB").resize((m.motion.SIZE,m.motion.SIZE),Image.Resampling.BILINEAR).tobytes()


@pytest.mark.parametrize("fmt",["SHORT","LONG"])
@pytest.mark.parametrize("count",[3,4,5])
def test_visual_invariance(fmt,count):
    base=synthetic(fmt,count)
    raw=png(base)
    variants=m.images(raw,fmt,count)
    assert variants==m.images(raw,fmt,count)
    for i,variant in enumerate(variants):
        with Image.open(io.BytesIO(variant)) as im:
            after=im.convert("RGB")
        box=m.row_boxes(fmt,count)[i]
        diff=ImageChops.difference(base,after)
        bound=diff.getbbox()
        assert bound and box[0]<=bound[0]<=bound[2]<=box[2] and box[1]<=bound[1]<=bound[3]<=box[3]
        before_bytes=base.crop(box).tobytes()
        after_bytes=after.crop(box).tobytes()
        assert len(before_bytes)==len(after_bytes)
        for p in range(0,len(before_bytes),3):
            old,new=before_bytes[p:p+3],after_bytes[p:p+3]
            assert new==old or (old==bytes(m.BACKGROUND) and new==bytes(m.ACTIVE))
    row=list(zip(m.stages(25,count),variants))
    data=b"".join(low(raw)*n for n,raw in row)
    assert m.motion.frame_check(data,[row])["frames_compared"]==25
    with pytest.raises(ValueError,match="MOTION_FRAME_MISMATCH"):
        m.motion.frame_check(low(variants[1])+data[m.motion.BYTES:],[row])


@pytest.mark.parametrize("fmt,count",[("OTHER",3),("SHORT",2),("LONG",6),("SHORT",True)])
def test_bad_layout(fmt,count):
    with pytest.raises(ValueError):m.row_boxes(fmt,count)


def test_wrong_size():
    with pytest.raises(ValueError,match="CHART_IMAGE"):
        m.images(png(Image.new("RGB",(50,50))),"SHORT",3)


def test_missing_background():
    with pytest.raises(ValueError,match="CHART_BACKGROUND"):
        m.images(png(Image.new("RGB",(720,1280))),"SHORT",3)


def test_incomplete(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="MOTION_INVENTORY"):m.verify((),None,PIN,b"",PIN,tmp_path,PIN)


def test_receipt():
    child={"duration_ms":2000}
    obj=m.receipt(PIN,"b"*64,{"hindi":child,"english":child})
    assert not obj["publication_eligible"] and not obj["editorial_queue_created"]
    with pytest.raises(ValueError,match="DURATION"):
        m.receipt(PIN,"b"*64,{"hindi":child,"english":{"duration_ms":2040}})
