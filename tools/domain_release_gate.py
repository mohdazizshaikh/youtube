#!/usr/bin/env python3
"""Offline 12-domain / 24-video artifact-and-attestation checklist.

Verifies *local bytes*, required specialist evidence fields and manually entered
owner/expert review flags. It does not independently determine truth, copyright
ownership, monetization eligibility or footage originality. A passing metadata
check is NEVER equivalent to legal or editorial release approval.

This tool never downloads videos, calls APIs or publishes anything.
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.domain_adapters import POLICIES

FORMATS=('SHORT','LONG')
MAX_LOCAL_FILE=500*1024*1024


def matrix_template() -> dict:
    return {'schema':'VIRALOS_DOMAIN_24_VIDEO_ACCEPTANCE_V1',
            'status':'PLANNED_NEEDS_REAL_VIDEO_AND_HUMAN_REVIEW',
            'owner_acceptance_verified':False,'records':[
                {'domain':d,'format':fmt,'video_path':None,'video_sha256':None,
                 'claims_manifest_path':None,'claims_manifest_sha256':None,
                 'rights_manifest_path':None,'rights_manifest_sha256':None,
                 'domain_expert':None,'domain_expert_checked_sources':False,
                 'owner_checked_full_video':False,'owner_checked_originality':False,
                 'owner_checked_music_footage_rights':False,
                 'owner_checked_on_screen_disclosures':False,
                 'locale_checked_by_native_speaker':False,'review_notes':None}
                for d in POLICIES for fmt in FORMATS]}


def _safe_asset(root:Path, relative:str|None, expected_sha:str|None):
    if not isinstance(relative,str) or not isinstance(expected_sha,str):
        return 'ARTIFACT_OR_HASH_MISSING'
    p=PurePosixPath(relative)
    if p.is_absolute() or str(p)!=relative or '..' in p.parts or '\\' in relative or not relative:
        return 'UNSAFE_ARTIFACT_PATH'
    if len(expected_sha)!=64 or any(ch not in '0123456789abcdef' for ch in expected_sha):
        return 'INVALID_SHA256'
    candidate=root/relative
    cursor=root
    for part in p.parts:
        cursor=cursor/part
        if cursor.is_symlink():
            return 'SYMLINK_NOT_ALLOWED'
    file=candidate.resolve()
    if not file.is_relative_to(root) or not file.is_file():
        return 'ARTIFACT_NOT_FOUND_OR_UNSAFE'
    if file.stat().st_size==0 or file.stat().st_size>MAX_LOCAL_FILE:
        return 'ARTIFACT_SIZE_NOT_ALLOWED'
    digest=hashlib.sha256()
    with file.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            digest.update(block)
    return None if digest.hexdigest()==expected_sha else 'ARTIFACT_HASH_MISMATCH'


def evaluate(manifest:dict,root:Path) -> dict:
    if not isinstance(manifest,dict) or manifest.get('schema')!='VIRALOS_DOMAIN_24_VIDEO_ACCEPTANCE_V1':
        raise ValueError('Invalid domain acceptance manifest schema')
    entries=manifest.get('records')
    if not isinstance(entries,list) or len(entries)!=24:
        raise ValueError('Manifest requires exactly 12 domains × 2 format records')
    root=Path(root).resolve()
    if not root.is_dir():raise ValueError('Local evidence root missing')
    expected={(d,f) for d in POLICIES for f in FORMATS}; seen=set();report=[]
    for item in entries:
        if not isinstance(item,dict):raise ValueError('Each domain record must be a JSON object')
        key=(item.get('domain'),item.get('format'))
        if key not in expected or key in seen:
            raise ValueError('Unexpected or duplicate domain/format record')
        seen.add(key)
        blockers=[]
        for field,hash_field in [('video_path','video_sha256'),('claims_manifest_path','claims_manifest_sha256'),
                                 ('rights_manifest_path','rights_manifest_sha256')]:
            error=_safe_asset(root,item.get(field),item.get(hash_field))
            if error:blockers.append(field+':'+error)
        for flag in ('domain_expert_checked_sources','owner_checked_full_video','owner_checked_originality',
                     'owner_checked_music_footage_rights','owner_checked_on_screen_disclosures',
                     'locale_checked_by_native_speaker'):
            if item.get(flag) is not True:blockers.append(flag+':HUMAN_ATTESTATION_MISSING')
        for field in ('domain_expert','review_notes'):
            if not isinstance(item.get(field),str) or len(item[field].strip())<8:
                blockers.append(field+':REVIEW_IDENTITY_OR_NOTES_MISSING')
        report.append({'domain':key[0],'format':key[1],
                       'artifact_integrity_and_manual_metadata_complete':not blockers,
                       'blockers':blockers})
    complete=sum(x['artifact_integrity_and_manual_metadata_complete'] for x in report)
    return {'gate':'TWELVE_DOMAIN_SHORT_LONG_LOCAL_EVIDENCE',
            'checks_complete':complete,'checks_required':24,
            'all_artifact_hashes_and_attestations_present':complete==24,
            'individual_results':report,
            'facts_independently_verified_by_tool':False,
            'media_licensing_legally_certified':False,
            'videos_watched_by_tool':False,
            'public_publishing_allowed':False,
            'twelve_fully_operational_ai_domains_proven':False,
            'remote_contacts_made':False}


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--evidence-root',type=Path,required=True)
    ap.add_argument('--report',type=Path)
    args=ap.parse_args(argv)
    result=evaluate(json.loads(args.manifest.read_text('utf8')),args.evidence_root)
    if args.report:
        if args.report.exists():ap.error('Do not overwrite a previous acceptance evidence report')
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'checks_complete':result['checks_complete'],'checks_required':24,
                      'public_publishing_allowed':False,'real_ai_domain_systems_proven':False},indent=2))
    return 0 if result['all_artifact_hashes_and_attestations_present'] else 2

if __name__=='__main__':raise SystemExit(main())
