"""SQLite consistent snapshot and fail-closed recovery tests, no network."""
import os
from zipfile import ZipFile, ZIP_DEFLATED
import pytest
from app import db
from tools.offline_backup_restore import make_backup,verify_backup,restore_backup


def test_sqlite_backup_verify_restore_refuses_overwrite(tmp_path,monkeypatch):
    monkeypatch.setenv('VIRALOS_DB',str(tmp_path/'data'/'viral.db'))
    db.initialize()
    outputs=tmp_path/'outputs'
    outputs.mkdir()
    (outputs/'original-caption.txt').write_text('हिंदी cricket caption',encoding='utf8')
    destination=tmp_path/'private'/'backup.viralbackup.zip'
    result=make_backup(destination,db.path(),outputs)
    assert result['file_count']==2 and '009' in result['migrations']
    assert verify_backup(destination)['verified']
    restored=tmp_path/'restore'/'empty'
    assert restore_backup(destination,restored)['file_count']==2
    assert (restored/'outputs'/'original-caption.txt').read_text(encoding='utf8')=='हिंदी cricket caption'
    assert (restored/'data'/'viral.db').exists()
    with pytest.raises(ValueError,match='empty'):
        restore_backup(destination,restored)
    with pytest.raises(ValueError,match='exists'):
        make_backup(destination,db.path(),outputs)


def test_tampered_backup_and_zip_slip_fail_before_restore(tmp_path,monkeypatch):
    monkeypatch.setenv('VIRALOS_DB',str(tmp_path/'db.sqlite'))
    db.initialize()
    archive=tmp_path/'backup.viralbackup.zip'
    make_backup(archive,db.path(),tmp_path/'none')
    altered=tmp_path/'altered.viralbackup.zip'
    with ZipFile(archive) as src, ZipFile(altered,'w',compression=ZIP_DEFLATED) as dest:
        for name in src.namelist():
            data=src.read(name)
            if name=='data/viral.db':data+=b'BROKEN'
            dest.writestr(name,data)
    with pytest.raises(ValueError,match='checksum'):
        verify_backup(altered)
    unsafe=tmp_path/'unsafe.viralbackup.zip'
    with ZipFile(unsafe,'w') as z:
        z.writestr('manifest.json','{}')
        z.writestr('../evil.txt',b'bad')
    with pytest.raises(ValueError):
        restore_backup(unsafe,tmp_path/'new')
