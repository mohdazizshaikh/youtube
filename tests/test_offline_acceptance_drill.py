"""Synthetic disaster recovery is testable without ever seeing owner data."""
import sqlite3
from tools.offline_acceptance_drill import run_drill


def test_fixture_backup_restore_and_checksum_no_private_data(tmp_path):
    report=run_drill(tmp_path/'isolated')
    assert report['status']=='SYNTHETIC_RESTORE_INTEGRITY_PASSED'
    assert report['sqlite_integrity_check']=='ok'
    assert report['artifact_sha256_match']
    assert report['schema_migrations_count']>=12
    assert not report['real_owner_data_accessed']
    assert not report['real_windows_hardware_accepted']
    restored=sqlite3.connect(str(tmp_path/'isolated'/'restored'/'data'/'viral.db'))
    try:assert restored.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    finally:restored.close()
