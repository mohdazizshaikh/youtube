import pytest
from tools import chart_review_dashboard as d, chart_pair_snapshot as s
from tools import bilingual_chart_pilot as c

PIN="a"*64


def receipt():
    rows=[{"scene":i,"source_id":"A","source_sha256":"b"*64,"data_sha256":"c"*64,
           "chart_request_sha256":"d"*64,"chart_sha256":"e"*64} for i in (1,2)]
    runs={l:{"manifest_sha256":("1" if l=="hindi" else "2")*64,"video_sha256":"3"*64,
             "duration_ms":1200} for l in d.LANGS}
    return c.receipt(PIN,"f"*64,1200,rows,runs)


def check(obj):
    raw=c.json_bytes(obj)
    return d.records(raw,c.sha(raw))


@pytest.mark.parametrize("field,value",[("schema","bad"),("pair_sha256",None),("request_sha256","bad"),
    ("duration_ms",1201),("duration_ms",True),("duration_ms",120040),("scenes",[]),("scenes",None),
    ("runs",{}),("runs",None),("visual_mode","ASCII_ONLY"),("caption_timing","WORD"),
    ("source_transcription_verified",True),("translation_verified",True),
    ("human_review_verified",True),("publication_eligible",True),("extra",1)])
def test_receipt_fields(field,value):
    obj=receipt()
    obj[field]=value
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("field,value",[("scene",2),("scene",True),("source_id","lower"),
    ("source_id",None),("source_sha256","bad"),("data_sha256","bad"),
    ("chart_request_sha256","bad"),("chart_sha256",None),("extra",1)])
def test_scene_fields(field,value):
    obj=receipt()
    obj["scenes"][0][field]=value
    with pytest.raises(ValueError):check(obj)


@pytest.mark.parametrize("field,value",[("manifest_sha256","2"*64),("video_sha256","bad"),
    ("duration_ms",1200.0),("duration_ms",1240),("extra",1)])
def test_run_fields(field,value):
    obj=receipt()
    obj["runs"]["hindi"][field]=value
    with pytest.raises(ValueError):check(obj)


def test_receipt():
    assert check(receipt())==receipt()


def scene():
    obj=receipt()
    row=obj["scenes"][0]
    declaration={"schema":"VIRALOS_CHART_SCENE_DECLARATION_V1","scene":1,"language":"hindi",
        "parent_board_sha256":"4"*64,"source_id":"A","source_sha256":row["source_sha256"],
        "data_sha256":row["data_sha256"],"chart_request_sha256":row["chart_request_sha256"],
        "chart_receipt_sha256":row["chart_sha256"],"png_sha256":"5"*64,
        "pair_sha256":obj["pair_sha256"],"pilot_request_sha256":obj["request_sha256"],
        "source_transcription_verified":False}
    packet={"scene":1,"board_sha256":"5"*64,"sources":[{"source_id":"A"}],
            "claims":[{"links":[{"source_id":"A","relation":"SUPPORTS"}]}],"specialist_facts":{}}
    return obj,row,packet,declaration


def binding(obj,row,packet,decl):
    packet["specialist_facts"][c.KEY]=c.json_bytes(decl).decode()
    d.scene_binding(packet,row,obj,"hindi")


@pytest.mark.parametrize("field,value",[("language","english"),("scene",2),("scene",True),
    ("source_id","B"),("source_sha256",PIN),("data_sha256",PIN),("chart_request_sha256",PIN),
    ("chart_receipt_sha256",PIN),("png_sha256",PIN),("parent_board_sha256","bad"),
    ("pair_sha256","0"*64),("pilot_request_sha256",PIN),("source_transcription_verified",True),
    ("extra",1)])
def test_scene_binding(field,value):
    obj,row,packet,decl=scene()
    decl[field]=value
    with pytest.raises(ValueError):binding(obj,row,packet,decl)


def test_source_support():
    obj,row,packet,decl=scene()
    binding(obj,row,packet,decl)
    packet["claims"][0]["links"][0]["relation"]="CONTEXT"
    with pytest.raises(ValueError,match="SOURCE_DECLARATION"):binding(obj,row,packet,decl)


def test_incomplete(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="CHART_PAIR_INVENTORY"):d.select_runs(tmp_path,PIN)
    with pytest.raises(ValueError,match="CHART_SNAPSHOT_INVENTORY"):s.inspect(tmp_path,PIN,PIN)
