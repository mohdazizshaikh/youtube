import re
import shutil
import pytest
from fastapi.testclient import TestClient
from tools import bilingual_review_dashboard as d
from tools import bilingual_pilot as p
from test_bilingual_compose import inputs
from test_bilingual_pilot import pair_inputs,values


@pytest.fixture
def fake_app(tmp_path,monkeypatch):
    runs={"hindi":(tmp_path/"hindi","a"*64,"b"*64),
          "english":(tmp_path/"english","c"*64,"d"*64)}
    monkeypatch.setattr(d,"select_runs",lambda *a:(runs,2080))
    def snap(r,duration,fresh=False):
        return {"duration_ms":duration,"read_only":True,"publication_eligible":False,
                "fresh_media_audit":fresh,"languages":{}}
    monkeypatch.setattr(d,"snapshot",snap)
    client=TestClient(d.create_app(tmp_path,"a"*64))
    token=re.search(r'name="review-session" content="([0-9a-f]{64})"',client.get("/").text).group(1)
    return client,{"X-Review-Session":token}


@pytest.mark.parametrize("path",["/","/dashboard.js","/dashboard.css"])
def test_static(fake_app,path):
    client,_=fake_app
    response=client.get(path)
    assert response.status_code==200
    assert response.headers["cache-control"]=="no-store"
    assert response.headers["x-frame-options"]=="DENY"
    assert "unsafe-inline" not in response.headers["content-security-policy"]


@pytest.mark.parametrize("headers",[{},{"X-Review-Session":"bad"},{"X-Review-Session":"0"*64}])
def test_session_required(fake_app,headers):
    client,_=fake_app
    assert client.get("/api/status",headers=headers).status_code==403


@pytest.mark.parametrize("header,value",[("host","evil.example"),("origin","https://evil.example"),
    ("sec-fetch-site","cross-site"),("sec-fetch-site","same-site")])
def test_browser_guard(fake_app,header,value):
    client,headers=fake_app
    assert client.get("/api/status",headers={**headers,header:value}).status_code==403


def test_status(fake_app):
    client,headers=fake_app
    result=client.get("/api/status",headers=headers)
    assert result.status_code==200 and result.json()["read_only"]
    assert not result.json()["publication_eligible"]


@pytest.mark.parametrize("path",["/api/status","/api/video/hindi","/api/submit","/api/register"])
def test_no_writes(fake_app,path):
    client,headers=fake_app
    assert client.post(path,headers=headers,json={}).status_code in (404,405)


@pytest.mark.parametrize("lang",["other","HINDI","native","123"])
def test_unknown_language(fake_app,lang):
    client,headers=fake_app
    assert client.get("/api/video/"+lang,headers=headers).status_code==404


def test_incomplete_pair(tmp_path):
    (tmp_path/"INCOMPLETE").touch()
    with pytest.raises(ValueError,match="PAIR_INVENTORY"):
        d.select_runs(tmp_path,"a"*64)


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),reason="local media tools required")
def test_real_dashboard(pair_inputs):
    v=values(pair_inputs)
    pair=p.build(*v)
    app=d.create_app(v[-1],pair["pair_sha256"])
    client=TestClient(app)
    token=re.search(r'name="review-session" content="([0-9a-f]{64})"',client.get("/").text).group(1)
    headers={"X-Review-Session":token}
    status=client.get("/api/status",headers=headers).json()
    assert status["duration_ms"]==2080
    for lang in d.LANGS:
        assert status["languages"][lang]["state"]=="PENDING"
        video=client.get("/api/video/"+lang,headers=headers)
        assert video.status_code==200
        assert p.sha(video.content)==pair["runs"][lang]["video_sha256"]
    (v[-1]/"hindi"/"draft"/"draft.mp4").write_bytes(b"tampered")
    assert client.get("/api/status",headers=headers).status_code==409
