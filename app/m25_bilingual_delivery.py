"""Offline, hash-bound bilingual (Hindi/English) technical delivery audit.

The two-language package must contain independent narration, localized script,
subtitles, video render, rights record and listening-review receipt per locale.
Only exact local bytes/codec/duration are verifiable; human fact, rights, visual
and subtitle-playback claims remain **unverified attestations**. No publishing.
"""
from __future__ import annotations
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath

from .m24_audio import wav_audio_qa
from .m25_audio_conformance import compare_narration_to_video

SHA = re.compile(r'^[0-9a-f]{64}$')
CAPTION_CLOCK = re.compile(r'^(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})$')
CHECKS = ('owner_checked_script_facts_and_names', 'native_speaker_checked_subtitles_and_graphics',
          'owner_watched_full_video_and_listened', 'owner_checked_media_rights_and_music',
          'owner_checked_ai_disclosures_and_originality')
FILES = {'script':('.txt',256*1024), 'captions':('.srt',256*1024),
         'voice':('.wav',40*1024*1024),'video':('.mp4',500*1024*1024),
         'rights_manifest':('.json',256*1024),'voice_review':('.json',256*1024)}


def _hash(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def _local_file(root:Path, evidence:dict, suffix:str, limit:int) -> Path:
    if not isinstance(evidence,dict) or set(evidence) != {'path','sha256'}:
        raise ValueError('Each local artifact requires exact path and sha256')
    name=evidence['path'];sha=evidence['sha256']
    if not isinstance(name,str) or not 1<=len(name)<=400 or not isinstance(sha,str) or not SHA.fullmatch(sha):
        raise ValueError('Missing or invalid artifact path/hash')
    pp=PurePosixPath(name)
    if (pp.is_absolute() or str(pp)!=name or name.startswith('.') or '\\' in name
            or any(part in ('','.','..') for part in pp.parts) or pp.suffix.lower()!=suffix):
        raise ValueError('Unsafe artifact relative path or extension')
    current=root
    for part in pp.parts:
        current=current/part
        if current.is_symlink():raise ValueError('Symlink evidence is never trusted')
    path=current.resolve()
    if not path.is_relative_to(root) or not path.is_file() or not 0<path.stat().st_size<=limit:
        raise ValueError('Missing, unsafe or oversized artifact')
    if _hash(path)!=sha:raise ValueError('Modified evidence file: '+name)
    return path


def _caption_text(path: Path, duration_ms: int) -> tuple[str, int]:
    """Inspect all timed SRT cues, not merely the presence of one timecode.

    Structural validation is automatic; actual subtitle visibility/readability
    and language accuracy still require a real owner watch-through.
    """
    content = path.read_text('utf8').replace('\r\n', '\n').strip()
    if not 1 <= len(content) <= 100000 or any(ord(c) == 0 for c in content):
        raise ValueError('Invalid caption text')
    blocks = re.split(r'\n\s*\n', content)
    if not 1 <= len(blocks) <= 1000:
        raise ValueError('SRT requires 1..1000 nonempty timestamped cues')
    transcript = []
    previous_end = 0
    for number, block in enumerate(blocks, 1):
        lines = [line.strip() for line in block.splitlines()]
        if len(lines) < 3 or lines[0] != str(number):
            raise ValueError('Missing/duplicate/nonconsecutive SRT cue index')
        matched = CAPTION_CLOCK.fullmatch(lines[1])
        if matched is None:
            raise ValueError('Every SRT cue needs exact HH:MM:SS,mmm timestamps')
        parts = [int(x) for x in matched.groups()]
        if any(parts[i] >= 60 for i in (1, 2, 5, 6)) or any(parts[i] >= 1000 for i in (3, 7)):
            raise ValueError('Invalid SRT minutes/seconds/milliseconds')
        start = ((parts[0]*60 + parts[1])*60 + parts[2])*1000 + parts[3]
        end = ((parts[4]*60 + parts[5])*60 + parts[6])*1000 + parts[7]
        if start < previous_end or end <= start or end > duration_ms + 250:
            raise ValueError('SRT cues overlap or exceed video duration')
        previous_end = end
        text = ' '.join(x for x in lines[2:] if x)
        if not text or '<' in text or '>' in text or any(ord(c) < 32 for c in text):
            raise ValueError('Empty or unsupported caption text')
        transcript.append(text)
    return ' '.join(transcript), len(blocks)


def _probe_mp4(path:Path, ffprobe:str|None) -> tuple[int,list[str]]:
    executable=ffprobe or shutil.which('ffprobe')
    if not executable:
        raise ValueError('Installed FFprobe required for technical video inspection')
    try:
        proc=subprocess.run([str(executable),'-v','error','-show_entries',
                             'format=duration:stream=codec_name,codec_type','-of','json',
                             '-protocol_whitelist','file,pipe',str(path)],
                            capture_output=True,timeout=30,check=False)
    except (OSError,subprocess.TimeoutExpired) as ex:
        raise ValueError('FFprobe inspection failed') from ex
    if proc.returncode or len(proc.stdout)>250000:
        raise ValueError('FFprobe rejected the video or returned excessive output')
    try:
        data=json.loads(proc.stdout)
        duration=round(float(data['format']['duration'])*1000)
        streams=data['streams']
    except (ValueError,KeyError,TypeError) as ex:
        raise ValueError('FFprobe did not return valid duration/streams') from ex
    if not 500<=duration<=21600000:
        raise ValueError('Video duration outside accepted limits')
    codecs=[s.get('codec_name') for s in streams]
    if not any(s.get('codec_type')=='video' and s.get('codec_name')=='h264' for s in streams):
        raise ValueError('A decoded H.264 video stream is required')
    if not any(s.get('codec_type')=='audio' for s in streams):
        raise ValueError('A video audio stream is required')
    return duration,codecs


def evaluate_bilingual_delivery(package:dict,root:Path,*,ffprobe:str|None=None,ffmpeg:str|None=None) -> dict:
    if not isinstance(package,dict) or set(package)!= {'schema','format','source_script_sha256',
                                                         'source_dependency_sha256','variants'}:
        raise ValueError('Exact bilingual delivery V1 schema required')
    if package['schema']!='VIRALOS_M25_BILINGUAL_DELIVERY_V1' or package['format'] not in ('SHORT','LONG'):
        raise ValueError('Unsupported bilingual delivery schema/format')
    for field in ('source_script_sha256','source_dependency_sha256'):
        if not isinstance(package[field],str) or not SHA.fullmatch(package[field]):
            raise ValueError('Unverifiable common source script/evidence link')
    root=Path(root).resolve(strict=True)
    if not root.is_dir():raise ValueError('Evidence root must be directory')
    variants=package['variants']
    if not isinstance(variants,list) or len(variants)!=2 or {x.get('locale') for x in variants if isinstance(x,dict)}!={'hi-IN','en-US'}:
        raise ValueError('Exactly one Hindi and one US-English review required')
    technical=[];voice_digests=set();video_digests=set();script_digests=set();blockers=[]
    for variant in variants:
        loc=variant['locale']
        required={'locale','source_script_sha256','source_dependency_sha256',
                  'script','captions','voice','video','rights_manifest','voice_review',
                  'reviewer_id','review_notes','checks'}
        if set(variant)!=required:
            raise ValueError('Missing/unknown locale artifact or review fields')
        if variant['source_script_sha256']!=package['source_script_sha256'] or \
                variant['source_dependency_sha256']!=package['source_dependency_sha256']:
            raise ValueError('Mixed or stale source material across localizations')
        paths={key:_local_file(root,variant[key],*FILES[key]) for key in FILES}
        contents=paths['script'].read_text('utf8')
        if not 20<=len(contents.strip())<=15000:
            raise ValueError('Reviewed local script length invalid')
        if loc=='hi-IN' and not any('\u0900'<=ch<='\u097f' for ch in contents):
            raise ValueError('Hindi delivery requires Devanagari script')
        qa=wav_audio_qa(paths['voice'])
        if qa['technical_flags']:blockers += [loc+':AUDIO_'+x for x in qa['technical_flags']]
        dur,codecs=_probe_mp4(paths['video'],ffprobe)
        conformance=compare_narration_to_video(paths['voice'],paths['video'],ffmpeg=ffmpeg)
        if not conformance['acoustically_consistent']:
            blockers.append(loc+':MP4_AUDIO_NOT_CONSISTENT_WITH_REVIEWED_NARRATION')
        caption_text, caption_cues = _caption_text(paths['captions'], dur)
        if ' '.join(contents.split()).casefold() != ' '.join(caption_text.split()).casefold():
            raise ValueError('Exact localized transcript and SRT text disagree')
        if package['format']=='SHORT' and dur>180000:
            blockers.append(loc+':SHORT_DURATION_EXCEEDS_180S')
        if abs(qa['duration_ms']-dur)>2500:
            blockers.append(loc+':VIDEO_VOICE_DURATION_DISAGREEMENT')
        receipt=json.loads(paths['voice_review'].read_text('utf8'))
        if not isinstance(receipt,dict) or receipt.get('schema')!='VIRALOS_M24_HUMAN_VOICE_REVIEW_V1' or \
                receipt.get('locale')!=loc or receipt.get('audio_sha256')!=qa['audio_sha256'] or \
                receipt.get('status')!='HUMAN_LISTENING_ATTESTED_NOT_INDEPENDENTLY_VERIFIED' or \
                receipt.get('blockers')!=[]:
            blockers.append(loc+':M24_LISTENING_RECORD_MISSING_OR_MISMATCHED')
        if not isinstance(receipt, dict) or receipt.get('text_sha256') != _hash(paths['script']):
            blockers.append(loc+':M24_VOICE_TEXT_NOT_BOUND_TO_REVIEWED_SCRIPT')
        try:
            rights=json.loads(paths['rights_manifest'].read_text('utf8'))
        except (ValueError,UnicodeError) as ex:
            raise ValueError('Unreadable rights metadata') from ex
        if not isinstance(rights,dict) or rights.get('owner_rights_reviewed') is not True or \
                not isinstance(rights.get('source_references'),list) or not rights['source_references']:
            blockers.append(loc+':MEDIA_RIGHTS_REFERENCE_MISSING')
        checks=variant['checks']
        if not isinstance(checks,dict) or set(checks)!=set(CHECKS):
            raise ValueError('Expected explicit owner review checklist')
        blockers.extend(loc+':'+flag.upper()+'_NOT_ATTESTED' for flag in CHECKS if checks[flag] is not True)
        reviewer,notes=variant['reviewer_id'],variant['review_notes']
        if not isinstance(reviewer,str) or not 3<=len(reviewer.strip())<=100 or \
                not isinstance(notes,str) or not 20<=len(notes.strip())<=1500:
            blockers.append(loc+':OWNER_REVIEW_ID_OR_NOTES_INCOMPLETE')
        script_digests.add(variant['script']['sha256']);voice_digests.add(variant['voice']['sha256'])
        video_digests.add(variant['video']['sha256'])
        technical.append({'locale':loc,'video_duration_ms':dur,'voice_duration_ms':qa['duration_ms'],
                          'video_codecs':codecs,'script_sha256':variant['script']['sha256'],
                          'video_sha256':variant['video']['sha256'],'voice_sha256':qa['audio_sha256'],
                          'caption_sha256':variant['captions']['sha256'],
                          'caption_cues_structurally_verified':caption_cues,
                          'mp4_narration_audio_conformance':conformance})
    if len(script_digests)!=2 or len(voice_digests)!=2 or len(video_digests)!=2:
        blockers.append('LANGUAGES_REUSE_IDENTICAL_SCRIPT_VOICE_OR_VIDEO')
    return {'schema':'VIRALOS_M25_BILINGUAL_DELIVERY_AUDIT_V1',
            'status':'OFFLINE_TWO_LOCALE_FILES_VERIFIED_OWNER_REVIEW_ATTESTED' if not blockers else 'BLOCKED',
            'format':package['format'],'source_script_sha256':package['source_script_sha256'],
            'source_dependency_sha256':package['source_dependency_sha256'],
            'technical_results':technical,'blockers':sorted(set(blockers)),
            'local_artifact_hashes_verified':True,'video_audio_contains_exact_reviewed_voice_proven':False,
            'sampled_mp4_audio_consistency_checked':True,
            'all_sources_independently_fact_checked_by_tool':False,
            'human_review_identity_independently_authenticated':False,
            'media_rights_legally_certified':False,
            'studio_readability_independently_evaluated':False,
            'publish_ready':False,'automatic_translation_used':False,
            'youtube_upload_authorized':False,'network_requests':False}
