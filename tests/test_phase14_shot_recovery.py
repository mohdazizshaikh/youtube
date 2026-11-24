import pytest
try:
    from tools import phase14_shot_recovery as r
except ImportError:
    import phase14_shot_recovery as r

def test_snapshot_partial(tmp_path):
    (tmp_path/'INCOMPLETE').touch();(tmp_path/'shot.mp4').write_bytes(b'damaged')
    first=r.snapshot(tmp_path);assert set(first)=={'INCOMPLETE','shot.mp4'}
    (tmp_path/'shot.mp4').write_bytes(b'changed');assert first!=r.snapshot(tmp_path)

def test_snapshot_unknown_file(tmp_path):
    (tmp_path/'INCOMPLETE').touch();(tmp_path/'unrelated').touch()
    with pytest.raises(ValueError,match='inventory'):r.snapshot(tmp_path)

def test_completed_not_recovery_source(tmp_path):
    with pytest.raises(ValueError,match='incomplete'):r.snapshot(tmp_path)

def test_invalid_selector_rejected():
    with pytest.raises(ValueError,match='selector'):r.recover('x','a'*64,'../x','x','b'*64,'x','x')
