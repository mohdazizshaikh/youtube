#!/usr/bin/env python3
"""READ-ONLY inventory/diff for an owner-held local ViralOS backup or ZIP.

Never connects to either GitHub account, executes source code or unpacks a ZIP.
Never copies candidate files, rewrites the current working tree or automatically
merges a migration. Output is metadata-only. Keep reports off public Git until
reviewed: even paths/filenames may reveal local project details.

  python tools/reconcile_owner_backup.py --candidate C:/Private/my-old-backup.zip \
      --current-root . --output C:/Private/reconciliation.json
"""
from __future__ import annotations
import argparse,hashlib,json,re,stat,sys
from pathlib import Path,PurePosixPath
from zipfile import ZipFile

IGNORED_PARTS={'.git','.venv','venv','node_modules','__pycache__','.pytest_cache',
               '.next','outputs','data','.idea','dist','build'}
PRIVATE_NAMES={'.env','.env.local','.env.production','credentials.json','client_secret.json',
               'token.json','oauth.json','cookies.txt','.pypirc','.npmrc','id_rsa'}
BYTE_LIMIT=500*1024*1024
FILE_LIMIT=50_000


def _sha_stream(f):
    d=hashlib.sha256();size=0
    for chunk in iter(lambda:f.read(1024*1024),b''):
        size+=len(chunk)
        if size>BYTE_LIMIT:raise ValueError('File too large for safe offline candidate inventory')
        d.update(chunk)
    return d.hexdigest()


def _safe(relative:str)->bool:
    p=PurePosixPath(relative)
    return (bool(relative) and relative==str(p) and not p.is_absolute()
            and not relative.startswith('/') and '\\' not in relative and '..' not in p.parts)


def _ignored(name:str)->bool:
    parts=PurePosixPath(name).parts
    return bool(set(parts)&IGNORED_PARTS) or any(part in PRIVATE_NAMES or part.startswith('.env.') for part in parts)


def _zip_inventory(archive:Path):
    result={}
    with ZipFile(archive) as z:
        files=[info for info in z.infolist() if not info.is_dir()]
        if len(files)>FILE_LIMIT:raise ValueError('Candidate has too many ZIP files')
        seen=set()
        for info in files:
            name=info.filename
            if not _safe(name) or name in seen:
                raise ValueError('Unsafe/duplicate ZIP entry; manual archive inspection required')
            seen.add(name)
            mode=(info.external_attr >> 16)&0o170000
            if mode==stat.S_IFLNK:
                raise ValueError('Symlink archive entries are forbidden')
            if _ignored(name):continue
            if info.file_size>BYTE_LIMIT:raise ValueError('Candidate file exceeds local safety budget')
            with z.open(info) as f:
                digest=_sha_stream(f)
            result[name]={'sha256':digest,'bytes':info.file_size}
    return result


def _dir_inventory(root:Path):
    result={}
    # Walking Python filesystem does not follow directory symlinks by default.
    for p in root.rglob('*'):
        rel=p.relative_to(root).as_posix()
        if _ignored(rel):continue
        if p.is_symlink():raise ValueError('Owner backup contains symlink: '+rel)
        if p.is_file():
            if len(result)>=FILE_LIMIT:raise ValueError('Owner backup has too many files')
            if p.stat().st_size>BYTE_LIMIT:raise ValueError('Candidate file too large')
            with p.open('rb') as f:digest=_sha_stream(f)
            result[rel]={'sha256':digest,'bytes':p.stat().st_size}
    return result


def inventory(p:Path)->dict:
    p=p.resolve()
    if p.is_file() and p.suffix.lower()=='.zip':return _zip_inventory(p)
    if p.is_dir():return _dir_inventory(p)
    raise ValueError('Use a local owner-held .zip or directory; remote URLs are forbidden')


def compare(candidate:dict,current:dict)->dict:
    added=sorted(set(candidate)-set(current))
    modified=sorted(p for p in candidate.keys() & current.keys() if candidate[p]['sha256']!=current[p]['sha256'])
    identical=sorted(p for p in candidate.keys() & current.keys() if candidate[p]['sha256']==current[p]['sha256'])
    baseline_only=sorted(set(current)-set(candidate))
    migration_collisions=[p for p in modified if re.fullmatch(r'sql/\d{3}_[^/]+\.sql',p)]
    return {'schema':'VIRALOS_OWNER_BACKUP_RECONCILIATION_V1',
            'source':'OFFLINE_OWNER_HELD_SNAPSHOT','remote_contacted':False,'files_copied':False,
            'automatic_merge_performed':False,
            'candidate_file_count':len(candidate),'current_file_count':len(current),
            'new_paths':added,'modified_paths_REQUIRE_REVIEW':modified,
            'identical_count':len(identical),'current_only_count':len(baseline_only),
            'migration_checksum_conflicts_NEVER_AUTO_MERGE':migration_collisions,
            'requires_manual_source_rights_and_secret_review':True,
            'candidate_secret_paths_excluded':True,
            'ready_for_automatic_import':False}


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate',required=True,type=Path)
    ap.add_argument('--current-root',type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args(argv)
    if args.output.exists():ap.error('Refusing overwrite of an existing private reconciliation report')
    if args.output.resolve().is_relative_to(args.current_root.resolve()):
        ap.error('Report must be stored OUTSIDE source tree, not committed to public Git')
    result=compare(inventory(args.candidate),inventory(args.current_root))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in result.items() if isinstance(v,(bool,int))},indent=2))

if __name__=='__main__': main()
