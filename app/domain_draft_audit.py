"""Offline technical audit of a Phase 8 domain draft; never grants release rights.
Inputs are local owner-selected files. Manifest pin is an external trust anchor,
not a signature or proof of a human review. Sampled visuals/audio are not exhaustive.
"""
from __future__ import annotations
import hashlib
import html
import io
import json
import shutil
import subprocess
import wave
from array import array
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from .domain_draft_video import DraftPlan, _read_pcm, _vtt, RATE, FPS, digest
from .m25_audio_conformance import _decoded_track, _mono_pcm16_wav, _waveform_score


def _file(root: Path, name: str, max_bytes: int) -> Path:
    p = root / name
    if p.is_symlink() or not p.is_file() or not 0 < p.stat().st_size <= max_bytes:
        raise ValueError(f'missing, unsafe or oversized file: {name}')
    return p


def _hash(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def _run(args: list[str], timeout: int = 45) -> bytes:
    try:
        return subprocess.check_output(args, timeout=timeout, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        raise ValueError('local media verification failed') from e


def audit(draft: Path, assets: Path, manifest_pin: str) -> dict:
    draft, assets = Path(draft), Path(assets)
    if draft.is_symlink() or assets.is_symlink() or not draft.is_dir() or not assets.is_dir():
        raise ValueError('local non-symlink directories required')
    manifest_bytes = _file(draft, 'manifest.json', 128_000).read_bytes()
    if digest(manifest_bytes) != manifest_pin:
        raise ValueError('external manifest pin mismatch')
    m = json.loads(manifest_bytes)
    plan = DraftPlan.model_validate_json(_file(draft, 'plan.json', 128_000).read_bytes())
    first = plan.scenes[0].board
    if (m.get('schema'),m.get('domain'),m.get('format'),m.get('synthetic_demo')) != ('VIRALOS_DOMAIN_NARRATED_DRAFT_V1',first.domain,first.format,first.synthetic_demo):
        raise ValueError('manifest/plan identity mismatch')
    if any(m.get(k) is not False for k in ('publication_eligible','rights_cleared','claim_truth_verified','speech_content_verified','caption_word_alignment_verified')) or m.get('stream_qc_passed') is not True:
        raise ValueError('draft must remain non-publishable and unverified')
    names = {'plan.json','captions.vtt','narration.wav','draft.mp4'} | {f'scene_{i+1:02}.png' for i in range(len(plan.scenes))}
    if set(m.get('files_sha256',{})) != names or {p.name for p in draft.iterdir()} != names | {'manifest.json'}:
        raise ValueError('unexpected or missing draft inventory')
    for name in sorted(names):
        bound = 128*1024*1024 if name=='draft.mp4' else 8*1024*1024
        if _hash(_file(draft,name,bound)) != m['files_sha256'][name]:
            raise ValueError(f'file hash mismatch: {name}')
    start = 0; captions=['WEBVTT','']; expected_pcm=bytearray(); records=[]
    dims = (720,1280) if first.format=='SHORT' else (1280,720)
    for i,s in enumerate(plan.scenes):
        pcm,n = _read_pcm(assets,s)
        end=start+n
        name=f'scene_{i+1:02}.png'
        records.append({'scene':i+1,'start_ms':start*40,'end_ms':end*40,'frames':n,
                        'board_file':name,'board_sha256':m['files_sha256'][name],
                        'source_declaration_sha256':digest(json.dumps(s.board.model_dump(),sort_keys=True,ensure_ascii=False).encode()),
                        'narration_input_sha256':s.narration_sha256,'narration_pcm_sha256':digest(pcm),
                        'caption_text_sha256':digest(s.narration_text.encode()),'rights_self_attested':True})
        with Image.open(draft/name) as img:
            if img.format != 'PNG' or img.size != dims:
                raise ValueError('board dimensions or type mismatch')
            img.verify()
        captions += [f'{_vtt(start*40)} --> {_vtt(end*40)}',html.escape(s.narration_text,quote=False),'']
        expected_pcm.extend(pcm); start=end
    if m.get('scenes') != records or (m.get('frames'),m.get('fps'),m.get('duration_ms')) != (start,FPS,start*40) or start>FPS*(60 if first.format=='SHORT' else 120):
        raise ValueError('scene timing or declaration mismatch')
    if (draft/'captions.vtt').read_text(encoding='utf8') != '\n'.join(captions)+'\n':
        raise ValueError('caption content or timing mismatch')
    with wave.open(str(draft/'narration.wav'),'rb') as w:
        if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getcomptype(),w.getnframes()) != (1,2,RATE,'NONE',start*640) or w.readframes(w.getnframes()) != expected_pcm:
            raise ValueError('combined narration differs from original scene PCM')
    ffmpeg,ffprobe=shutil.which('ffmpeg'),shutil.which('ffprobe')
    if not ffmpeg or not ffprobe: raise ValueError('local FFmpeg and ffprobe required')
    video=draft/'draft.mp4'
    probe=json.loads(_run([ffprobe,'-v','error','-protocol_whitelist','file,pipe','-show_streams','-show_format','-of','json',str(video)]))
    streams=probe['streams']; vs=[s for s in streams if s['codec_type']=='video']; au=[s for s in streams if s['codec_type']=='audio']
    if len(streams)!=2 or len(vs)!=1 or len(au)!=1 or vs[0].get('codec_name')!='h264' or au[0].get('codec_name')!='aac' or (vs[0]['width'],vs[0]['height'])!=dims or int(vs[0].get('nb_frames','0'))!=start or abs(float(probe['format']['duration'])-start/FPS)>.15:
        raise ValueError('actual MP4 streams/frame count/duration mismatch')
    actual=_decoded_track(video,ffmpeg); ref=_mono_pcm16_wav(draft/'narration.wav')
    if abs(len(actual)-len(ref))>RATE*.15: raise ValueError('decoded audio duration mismatch')
    scores=[]
    for r in records:
        lo=r['start_ms']*16; hi=r['end_ms']*16
        segment=actual[lo:hi]
        observed_fraction=len(segment)/(hi-lo)
        if observed_fraction<.9: raise ValueError('scene decoded audio coverage too low')
        # AAC may trim a small final partial frame. Report actual coverage before zero padding.
        segment.extend(array('h',[0])*(hi-lo-len(segment)))
        score,lag,coverage=_waveform_score(ref[lo:hi],segment,scene_sync=True)
        if score<.65 or coverage<.8 or abs(lag)>100: raise ValueError('scene narration acoustic mismatch')
        # Midpoint visual sample. Compare 64x64 RGB to declared PNG; not frame exhaustive.
        middle=(r['start_ms']+r['end_ms'])/2000
        raw=_run([ffmpeg,'-nostdin','-hide_banner','-loglevel','error','-protocol_whitelist','file,pipe','-ss',f'{middle:.3f}','-i',str(video),'-map','0:v:0','-frames:v','1','-threads','1','-vf','scale=64:64','-f','rawvideo','-pix_fmt','rgb24','pipe:1'])
        if len(raw)!=64*64*3: raise ValueError('missing sampled video frame')
        with Image.open(draft/r['board_file']) as board:
            expected=board.convert('RGB').resize((64,64),Image.Resampling.BILINEAR)
        mae=sum(ImageStat.Stat(ImageChops.difference(expected,Image.frombytes('RGB',(64,64),raw))).mean)/3
        if mae>12: raise ValueError('sampled scene visual mismatch')
        scores.append({'scene':r['scene'],'audio_correlation':round(score,4),'audio_offset_ms':lag,'sampled_visual_mae':round(mae,3),'decoded_scene_coverage':round(observed_fraction,4)})
    return {'schema':'VIRALOS_DOMAIN_DRAFT_AUDIT_V1','manifest_sha256':manifest_pin,'domain':first.domain,'format':first.format,'synthetic_demo':first.synthetic_demo,'technical_audit_passed':True,'scene_checks':scores,'publication_eligible':False,'human_source_rights_and_listening_review_required':True,'all_frames_or_words_verified':False,'manifest_pin_is_not_signature':True}
