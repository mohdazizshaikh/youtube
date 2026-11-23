import io,stat,zipfile
from pathlib import Path
import pytest
from tools.reconcile_owner_backup import inventory,compare

def test_backup_inventory_and_migration_conflict_read_only(tmp_path):
    current=tmp_path/'current';old=tmp_path/'old'; current.mkdir();old.mkdir()
    for root in (current,old):
        (root/'sql').mkdir();(root/'app').mkdir()
        (root/'app'/'main.py').write_text('same')
    (current/'sql'/'010_localization_review.sql').write_text('current migration')
    (old/'sql'/'010_localization_review.sql').write_text('untrusted old migration')
    (old/'app'/'extra.py').write_text('owner-only code')
    (old/'.env').write_text('SECRET=abcdef')
    result=compare(inventory(old),inventory(current))
    assert result['identical_count']==1
    assert result['new_paths']==['app/extra.py']
    assert result['migration_checksum_conflicts_NEVER_AUTO_MERGE']==['sql/010_localization_review.sql']
    assert '.env' not in str(result)
    assert not result['automatic_merge_performed'] and not result['remote_contacted']
    assert (old/'app'/'extra.py').read_text()=='owner-only code'


def test_malicious_zip_paths_symlinks_and_duplicate_rejected(tmp_path):
    archive=tmp_path/'bad.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('../outside.txt','exploit')
    with pytest.raises(ValueError,match='Unsafe'):
        inventory(archive)
    with zipfile.ZipFile(archive,'w') as z:
        info=zipfile.ZipInfo('link.py');info.create_system=3
        info.external_attr=(stat.S_IFLNK|0o777)<<16
        z.writestr(info,'../private')
    with pytest.raises(ValueError,match='Symlink'):
        inventory(archive)
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('app/x.py','1')
        z.writestr('app/x.py','2')
    with pytest.raises(ValueError,match='duplicate'):
        inventory(archive)
