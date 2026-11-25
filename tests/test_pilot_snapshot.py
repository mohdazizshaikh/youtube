"""Portable byte-level fixtures plus one separate real media integration test."""
import hashlib
import json
import sqlite3

import pytest

from tools import pilot_snapshot as s
from tools.pilot_run_verify import verify
from test_pilot_run_verify import run


@pytest.fixture
def stopped(run, monkeypatch):
    # Only this portable fixture skips media decoding; never used by the CLI.
    monkeypatch.setattr(s, "verify", lambda path, pin, fresh: verify(path, pin, fresh=False))
    return run


@pytest.fixture
def saved(stopped):
    root, pin = stopped
    # The fixture run is tmp_path itself; create a separate sibling path.
    dest = root.parent / (root.name + "-snapshot")
    result = s.backup(root, dest, pin)
    return root, pin, dest, result["snapshot_sha256"]


def test_snapshot_and_restore(saved):
    root, pin, snap, sp = saved
    meta = s.inspect(snap, sp, pin)
    assert meta["publication_eligible"] is False
    assert len(meta["files"]) == 14
    output = root.parent / (root.name + "-restored")
    result = s.restore(snap, output, sp, pin)
    assert result["queue_state"] == "PENDING"
    assert result["publication_eligible"] is False
    assert (output / "catalog.json").read_bytes() != (root / "catalog.json").read_bytes()
    assert verify(output, pin)["integrity_passed"]
    assert s.inspect(snap, sp, pin) == meta


@pytest.mark.parametrize("name", [
    "../escape", "/absolute", "C:/absolute", "assets/../x.wav", "assets/a/b.wav",
    "assets/a.wav:stream", "assets/con.wav", "assets/AUX.wav", "assets/COM1.wav",
    "assets/LPT9.wav", "assets/NUL.wav", "assets/prn.wav", "assets/a.WAV",
    "assets/a..wav", "assets/a .wav", "assets/.hidden.wav", "assets/a\\b.wav",
    "draft/scene_00.png", "draft/scene_09.png", "draft/extra.png",
    "reviews.sqlite-wal", "reviews.sqlite-shm", "secret.json", "INCOMPLETE",
])
def test_unsafe_inventory(stopped, name):
    root, _ = stopped
    names = list(s.inventory(root))
    names[0] = name
    with pytest.raises(ValueError):
        s.validate_names(names)


@pytest.mark.parametrize("field,value", [
    ("bytes", 0), ("bytes", -1), ("bytes", True), ("bytes", 1.0),
    ("bytes", 2_000_001), ("sha256", ""), ("sha256", "x"*64),
    ("sha256", "A"*64), ("sha256", 7), ("extra", "unknown"),
])
def test_invalid_record(stopped, field, value):
    root, _ = stopped
    records = s.inventory(root)
    records["run.json"][field] = value
    with pytest.raises(ValueError):
        s.validate_records(records)


@pytest.mark.parametrize("name", [
    "run.json", "review_packet.json", "review_template.json", "catalog.json",
    "reviews.sqlite", "draft/manifest.json", "draft/plan.json", "draft/draft.mp4",
    "draft/captions.vtt", "draft/narration.wav", "draft/scene_01.png",
    "draft/scene_02.png", "assets/voice1.wav", "assets/voice2.wav",
])
def test_snapshot_tamper(saved, name):
    root, pin, snap, sp = saved
    (snap / "payload" / name).write_bytes(b"tamper")
    output = root.parent / (root.name + "-restore")
    with pytest.raises((ValueError, OSError)):
        s.restore(snap, output, sp, pin)
    assert not output.exists()


@pytest.mark.parametrize("bad", ["", "0"*64, "A"*64, "z"*64])
def test_wrong_snapshot_pin(saved, bad):
    _, pin, snap, _ = saved
    with pytest.raises(ValueError):
        s.inspect(snap, bad, pin)


def test_wrong_manifest_pin(saved):
    _, _, snap, sp = saved
    with pytest.raises(ValueError):
        s.inspect(snap, sp, "0"*64)


def test_existing_destination(saved):
    root, pin, snap, sp = saved
    with pytest.raises(ValueError):
        s.restore(snap, root, sp, pin)


def test_nested_destination(saved):
    _, pin, snap, sp = saved
    with pytest.raises(ValueError):
        s.restore(snap, snap / "new", sp, pin)


def test_unknown_root_file(stopped):
    root, pin = stopped
    (root / "unexpected.txt").touch()
    dest = root.parent / (root.name + "-new")
    with pytest.raises(ValueError):
        s.backup(root, dest, pin)
    assert not dest.exists()


def test_failed_restore_marked(saved, monkeypatch):
    root, pin, snap, sp = saved
    def fail(*args, **kwargs):
        raise ValueError("simulated media failure")
    monkeypatch.setattr(s, "verify", fail)
    output = root.parent / (root.name + "-restore")
    with pytest.raises(ValueError):
        s.restore(snap, output, sp, pin)
    assert (output / "INCOMPLETE").exists()


def test_copy_rejects_changed_source(tmp_path):
    src, dst = tmp_path / "input", tmp_path / "output"
    src.write_bytes(b"abc")
    record = {"bytes": 3, "sha256": hashlib.sha256(b"xyz").hexdigest()}
    with pytest.raises(ValueError):
        s.copy_exact(src, dst, record, 10)


def test_preserve_queue_history(stopped):
    root, pin = stopped
    with sqlite3.connect(root / "reviews.sqlite") as db:
        db.execute("UPDATE drafts SET revision=1,state='DEMO_BLOCKED'")
        db.execute("INSERT INTO submissions VALUES(?,?,?,?,?)",
                   (pin, 1, "DEMO_BLOCKED", "b"*64, 1))
    snap = root.parent / (root.name + "-snapshot")
    sp = s.backup(root, snap, pin)["snapshot_sha256"]
    out = root.parent / (root.name + "-restored")
    result = s.restore(snap, out, sp, pin)
    assert result["queue_revision"] == 1
    assert result["queue_state"] == "DEMO_BLOCKED"
    assert (out / "reviews.sqlite").read_bytes() == (root / "reviews.sqlite").read_bytes()
