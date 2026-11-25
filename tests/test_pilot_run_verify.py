"""Synthetic Phase 13 run fixtures; no media, account or physical PC acceptance."""
import hashlib
import json
import sqlite3

import pytest

from tools.pilot_run_verify import verify, canonical, APP_ID, decode


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data), encoding="utf8")


@pytest.fixture
def run(tmp_path):
    d, a = tmp_path / "draft", tmp_path / "assets"
    d.mkdir()
    a.mkdir()
    common = {"domain": "technology", "format": "SHORT", "synthetic_demo": True,
              "publication_eligible": False}
    checks = ["source_accuracy", "narration_accuracy", "visual_accuracy",
              "asset_rights", "originality", "caption_accuracy"]
    m = dict(common, schema="VIRALOS_DOMAIN_NARRATED_DRAFT_V1", fps=25, frames=50,
             duration_ms=2000, stream_qc_passed=True, caption_word_alignment_verified=False,
             speech_content_verified=False, claim_truth_verified=False, rights_cleared=False,
             scenes=[])
    packet = dict(common, schema="VIRALOS_DOMAIN_DRAFT_REVIEW_PACKET_V1",
                  human_review_verified=False, technical_audit_passed=True, scenes=[], checks=checks)
    plan = {"scenes": []}
    for i in (1, 2):
        name = f"voice{i}.wav"
        audio = b"fixture" + bytes([i])
        (a / name).write_bytes(audio)
        board = f"scene_{i:02}.png"
        (d / board).write_bytes(audio)
        voice = f"scene {i}"
        plan["scenes"].append({"narration_file": name, "narration_sha256": digest(audio),
                               "narration_text": voice, "rights_attested": True})
        s = {"scene": i, "start_ms": (i-1)*1000, "end_ms": i*1000,
             "board_file": board, "board_sha256": digest(audio), "rights_self_attested": True}
        m["scenes"].append(dict(s, frames=25, narration_input_sha256=digest(audio),
                                caption_text_sha256=digest(voice.encode())))
        p = dict(s, narration_sha256=digest(audio), narration_text=voice)
        p["scene_sha256"] = canonical(p)
        packet["scenes"].append(p)
    write(d / "plan.json", plan)
    for name in ("draft.mp4", "captions.vtt", "narration.wav"):
        (d / name).write_bytes(name.encode())
    m["files_sha256"] = {p.name: digest(p.read_bytes()) for p in d.iterdir()}
    write(d / "manifest.json", m)
    pin = digest((d / "manifest.json").read_bytes())
    video = m["files_sha256"]["draft.mp4"]
    packet.update(manifest_sha256=pin, video_sha256=video)
    write(tmp_path / "review_packet.json", packet)
    pp = canonical(packet)
    write(tmp_path / "review_template.json", {"schema_version": "VIRALOS_DOMAIN_DRAFT_REVIEW_V1",
          "manifest_sha256": pin, "packet_sha256": pp, "reviewer": "", "scenes": [
              {"scene": p["scene"], "scene_sha256": p["scene_sha256"],
               "checks": dict.fromkeys(checks, "NOT_REVIEWED"), "notes": ""} for p in packet["scenes"]]})
    write(tmp_path / "catalog.json", [{"manifest_sha256": pin, "draft": str(d.resolve()),
                                      "assets": str(a.resolve())}])
    write(tmp_path / "run.json", dict(common, schema="VIRALOS_PILOT_RUN_V1",
          manifest_sha256=pin, video_sha256=video, scenes=2, duration_ms=2000,
          elapsed_seconds=1.0, technical_audit_passed=True, human_review_verified=False,
          console_configuration_valid=True, review_pending=True, live_account_tested=False))
    db = sqlite3.connect(tmp_path / "reviews.sqlite")
    try:
        db.executescript(f"""PRAGMA application_id={APP_ID}; PRAGMA user_version=1;
          CREATE TABLE drafts(manifest_sha256,packet_sha256,video_sha256,domain,format,
                              synthetic_demo,scene_count,revision,state);
          CREATE TABLE submissions(manifest_sha256,revision,state,review_sha256,blocker_count);""")
        db.execute("INSERT INTO drafts VALUES(?,?,?,?,?,?,?,?,?)",
                   (pin, pp, video, "technology", "SHORT", 1, 2, 0, "PENDING"))
        db.commit()
    finally:
        db.close()
    return tmp_path, pin


def test_valid_metadata_is_read_only_and_not_release(run):
    root, pin = run
    before = {str(p): digest(p.read_bytes()) for p in root.rglob("*") if p.is_file()}
    result = verify(root, pin)
    assert result["integrity_passed"] is True
    assert result["fresh_media_audit"] is False
    assert result["publication_eligible"] is False
    assert result["human_review_verified"] is False
    assert result["queue_state"] == "PENDING"
    assert before == {str(p): digest(p.read_bytes()) for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("field,value", [
    ("schema", "wrong"), ("manifest_sha256", "0"*64), ("video_sha256", "0"*64),
    ("domain", "other"), ("format", "LONG"), ("synthetic_demo", 1),
    ("synthetic_demo", False), ("publication_eligible", True),
    ("publication_eligible", 0), ("technical_audit_passed", False),
    ("technical_audit_passed", 1), ("human_review_verified", True),
    ("live_account_tested", True), ("console_configuration_valid", False),
    ("review_pending", 1), ("elapsed_seconds", -1), ("elapsed_seconds", True),
    ("elapsed_seconds", "1"), ("elapsed_seconds", float("nan")),
    ("scenes", 1), ("scenes", 9), ("scenes", True), ("scenes", 2.0),
    ("duration_ms", 1000), ("duration_ms", 2000.0),
])
def test_reject_receipt_tamper(run, field, value):
    root, pin = run
    path = root / "run.json"
    data = json.loads(path.read_text())
    data[field] = value
    write(path, data)
    with pytest.raises(ValueError):
        verify(root, pin)


@pytest.mark.parametrize("path", [
    "draft/manifest.json", "draft/plan.json", "draft/draft.mp4", "draft/captions.vtt",
    "draft/narration.wav", "draft/scene_01.png", "draft/scene_02.png",
    "assets/voice1.wav", "assets/voice2.wav", "review_packet.json",
    "review_template.json", "catalog.json", "run.json", "reviews.sqlite",
])
def test_missing_file_blocks(run, path):
    root, pin = run
    (root / path).unlink()
    with pytest.raises((OSError, ValueError)):
        verify(root, pin)


@pytest.mark.parametrize("path", [
    "draft/draft.mp4", "draft/captions.vtt", "draft/narration.wav",
    "draft/scene_01.png", "draft/scene_02.png", "assets/voice1.wav", "assets/voice2.wav",
])
def test_changed_media_blocks(run, path):
    root, pin = run
    (root / path).write_bytes(b"tampered")
    with pytest.raises(ValueError):
        verify(root, pin)


@pytest.mark.parametrize("path", ["INCOMPLETE", "draft/extra.png", "assets/extra.wav",
                                  "reviews.sqlite-wal", "reviews.sqlite-shm", "reviews.sqlite-journal"])
def test_unexpected_state_blocks(run, path):
    root, pin = run
    (root / path).touch()
    with pytest.raises(ValueError):
        verify(root, pin)


@pytest.mark.parametrize("sql", [
    "PRAGMA application_id=0", "PRAGMA user_version=2",
    "DELETE FROM drafts", "UPDATE drafts SET revision=1",
    "UPDATE drafts SET state='SELF_ATTESTED'", "UPDATE drafts SET scene_count=3",
    "UPDATE drafts SET packet_sha256='bad'", "UPDATE drafts SET synthetic_demo=0",
    "UPDATE drafts SET video_sha256='bad'", "UPDATE drafts SET state='UNKNOWN'",
    "UPDATE drafts SET revision=1,state='DEMO_BLOCKED'",
    "INSERT INTO drafts SELECT * FROM drafts",
])
def test_queue_mutations_block(run, sql):
    root, pin = run
    db = sqlite3.connect(root / "reviews.sqlite")
    try:
        db.execute(sql)
        db.commit()
    finally:
        db.close()
    with pytest.raises(ValueError):
        verify(root, pin)


@pytest.mark.parametrize("bad", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'])
def test_strict_json(bad):
    with pytest.raises(ValueError):
        decode(bad)


@pytest.mark.parametrize("bad", ["", "a"*63, "A"*64, "g"*64, "0"*64])
def test_wrong_pin(run, bad):
    with pytest.raises(ValueError):
        verify(run[0], bad)
