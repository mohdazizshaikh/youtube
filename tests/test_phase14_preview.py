"""Portable contracts; full media render is a separate local acceptance action."""
from pathlib import Path
import pytest
from tools import phase14_preview as p


def test_experiment():
    assert p.A == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    assert p.B == "185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381969"
    assert len(p.BITS) == 256 and sum(p.BITS) == 125


def test_frame_clock():
    assert p.stamp(0) == "00:00:00.000"
    assert p.stamp(24) == "00:00:01.000"
    assert p.stamp(86400) == "01:00:00.000"


def test_bilingual_story_contract():
    assert len(p.SCENES) == 4
    assert all(title and en and hi for title, en, hi in p.SCENES)
    assert all(any("\u0900" <= c <= "\u097f" for c in hi) for _, _, hi in p.SCENES)


def test_existing_output_not_overwritten(tmp_path):
    pytest.importorskip("PIL")
    sentinel = tmp_path / "sentinel"
    sentinel.write_text("preserve", encoding="utf-8")
    with pytest.raises(FileExistsError):
        p.render(tmp_path, Path("missing-font"))
    assert sentinel.read_text(encoding="utf-8") == "preserve"
