"""Local source-linked multi-scene drafts, with owner-provided PCM narration.
No source retrieval, professional voice certification, or release eligibility.
"""
from __future__ import annotations
import hashlib
import html
import json
import re
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .domain_storyboards import Storyboard, render_board

RATE = 16000
FPS = 25
SAMPLES_PER_FRAME = RATE // FPS
MAX_SECONDS = 120
MAX_SCENE_SECONDS = 30


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Scene(Strict):
    board: Storyboard
    narration_file: str = Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}\.wav$')
    narration_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    narration_text: str = Field(min_length=3, max_length=500)
    rights_attested: Literal[True]

    @field_validator('rights_attested', mode='before')
    @classmethod
    def explicit_attestation(cls, v):
        if v is not True:
            raise ValueError('explicit boolean rights self-attestation required')
        return v

    @model_validator(mode='after')
    def text_safe(self):
        if not self.narration_text.strip() or any(ord(c) < 32 for c in self.narration_text) or '-->' in self.narration_text:
            raise ValueError('single-line caption text required')
        return self


class DraftPlan(Strict):
    scenes: list[Scene] = Field(min_length=2, max_length=8)

    @model_validator(mode='after')
    def consistent(self):
        first = self.scenes[0].board
        if any((s.board.domain,s.board.format,s.board.synthetic_demo) != (first.domain,first.format,first.synthetic_demo) for s in self.scenes):
            raise ValueError('all scenes must share domain, format and demo classification')
        if len({s.narration_file.casefold() for s in self.scenes}) != len(self.scenes):
            raise ValueError('each scene needs a distinct narration asset')
        return self


def _read_pcm(root: Path, scene: Scene) -> tuple[bytes, int]:
    # Only leaf names are allowed; restrict both source and staged bytes.
    import io
    p = root / scene.narration_file
    if p.is_symlink() or not p.is_file():
        raise ValueError('narration must be a local non-symlink regular file')
    with p.open('rb') as f:
        data = f.read(2 * RATE * MAX_SCENE_SECONDS + 65537)
    if len(data) > 2 * RATE * MAX_SCENE_SECONDS + 65536 or digest(data) != scene.narration_sha256:
        raise ValueError('narration exceeds byte limit or hash differs')
    with wave.open(io.BytesIO(data), 'rb') as w:
        n = w.getnframes()
        if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getcomptype()) != (1,2,RATE,'NONE') or not RATE//2 <= n <= RATE*MAX_SCENE_SECONDS:
            raise ValueError('scene WAV must be 0.5–30 seconds, mono PCM16 16kHz')
        pcm = w.readframes(n)
    if len(pcm) != 2*n or not any(pcm):
        raise ValueError('truncated or silent narration')
    frames = (n + SAMPLES_PER_FRAME - 1)//SAMPLES_PER_FRAME
    return pcm + b'\0'*(2*(frames*SAMPLES_PER_FRAME-n)), frames


def _vtt(ms):
    h,r = divmod(ms,3600000); m,r = divmod(r,60000); s,ms = divmod(r,1000)
    return f'{h:02}:{m:02}:{s:02}.{ms:03}'


def compose(plan: DraftPlan, assets: Path, output: Path) -> dict:
    """Compose a bounded 25 fps draft, with exact PCM/frame boundaries and VTT.
    Never overwrites a directory. Failed renders remove their incomplete outputs.
    """
    plan = DraftPlan.model_validate(plan.model_dump())
    assets = Path(assets).resolve(strict=True)
    if not assets.is_dir(): raise ValueError('asset directory required')
    inputs = [_read_pcm(assets,s) for s in plan.scenes]
    frames = sum(n for _,n in inputs)
    limit = 60 if plan.scenes[0].board.format == 'SHORT' else MAX_SECONDS
    if frames > FPS * limit: raise ValueError('draft exceeds CPU duration budget')
    ffmpeg,ffprobe = shutil.which('ffmpeg'),shutil.which('ffprobe')
    if not ffmpeg or not ffprobe: raise RuntimeError('local FFmpeg and ffprobe required')
    output = Path(output).absolute()
    output.mkdir(parents=False, exist_ok=False)
    try:
        records=[]; captions=['WEBVTT','']; start=0
        (output/'plan.json').write_text(plan.model_dump_json(indent=2)+'\n',encoding='utf8')
        cmd=[ffmpeg,'-nostdin','-hide_banner','-loglevel','error','-n']
        for i,(scene,(pcm,n)) in enumerate(zip(plan.scenes,inputs)):
            board=output/f'scene_{i+1:02}.png'
            report=render_board(scene.board,board)
            end=start+n
            captions += [f'{_vtt(start*40)} --> {_vtt(end*40)}',html.escape(scene.narration_text,quote=False),'']
            records.append({'scene':i+1,'start_ms':start*40,'end_ms':end*40,'frames':n,
                            'board_file':board.name,'board_sha256':report['board_sha256'],
                            'source_declaration_sha256':report['input_sha256'],
                            'narration_input_sha256':scene.narration_sha256,
                            'narration_pcm_sha256':digest(pcm),'caption_text_sha256':digest(scene.narration_text.encode()),
                            'rights_self_attested':True})
            cmd += ['-protocol_whitelist','file,pipe','-loop','1','-framerate',str(FPS),'-t',f'{n/FPS:.3f}','-i',str(board)]
            start=end
        wav=output/'narration.wav'
        with wave.open(str(wav),'wb') as w:
            w.setparams((1,2,RATE,0,'NONE','not compressed'))
            for pcm,_ in inputs:w.writeframesraw(pcm)
        vtt=output/'captions.vtt';vtt.write_text('\n'.join(captions)+'\n',encoding='utf8')
        cmd += ['-protocol_whitelist','file,pipe','-i',str(wav)]
        video=output/'draft.mp4'; count=len(inputs)
        # Filter only generated images, never untrusted media or filter strings.
        graph=''.join(f'[{i}:v]setsar=1,setpts=PTS-STARTPTS[v{i}];' for i in range(count)) + ''.join(f'[v{i}]' for i in range(count))+f'concat=n={count}:v=1:a=0,setpts=N/({FPS}*TB)[v]'
        cmd += ['-filter_complex_threads','1','-filter_complex',graph,'-map','[v]','-map',f'{count}:a:0','-r',str(FPS),'-fps_mode','cfr','-t',f'{frames/FPS:.3f}','-c:v','libx264','-threads','2','-preset','veryfast','-pix_fmt','yuv420p','-c:a','aac','-b:a','64k','-movflags','+faststart',str(video)]
        subprocess.run(cmd,check=True,timeout=300,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        probe=json.loads(subprocess.check_output([ffprobe,'-v','error','-protocol_whitelist','file,pipe','-show_streams','-show_format','-of','json',str(video)],timeout=30))
        vs=[x for x in probe['streams'] if x['codec_type']=='video']; audio=[x for x in probe['streams'] if x['codec_type']=='audio']
        dims=(720,1280) if plan.scenes[0].board.format=='SHORT' else (1280,720)
        if len(vs)!=1 or len(audio)!=1 or (vs[0]['width'],vs[0]['height'])!=dims or int(vs[0].get('nb_frames','0'))!=frames or abs(float(probe['format']['duration'])-frames/FPS)>.04 or abs(float(vs[0]['duration'])-frames/FPS)>.04 or abs(float(audio[0]['duration'])-frames/FPS)>.04 or vs[0]['avg_frame_rate']!='25/1':
            raise ValueError('render failed stream/frame/duration QC')
        manifest={'schema':'VIRALOS_DOMAIN_NARRATED_DRAFT_V1','domain':plan.scenes[0].board.domain,'format':plan.scenes[0].board.format,'synthetic_demo':plan.scenes[0].board.synthetic_demo,'frames':frames,'fps':FPS,'duration_ms':frames*40,'scenes':records,'files_sha256':{p.name:digest(p.read_bytes()) for p in sorted(output.iterdir()) if p.is_file()},'stream_qc_passed':True,'caption_word_alignment_verified':False,'speech_content_verified':False,'claim_truth_verified':False,'rights_cleared':False,'publication_eligible':False}
        (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
        return manifest
    except BaseException:
        shutil.rmtree(output)
        raise
