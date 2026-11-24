"""Offline narration-segment motion preview; no release authority or speech recognition."""
import argparse
import hashlib
import io
import json
import math
import re
import subprocess
import time
import wave
from pathlib import Path

W, H, FPS, RATE = 1920, 1080, 30, 48000
SAMPLES = RATE // FPS
VISUALS = ('file', 'compare', 'fingerprint')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def run(*args, timeout=180):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=timeout)


def read_voice(blob):
    with wave.open(io.BytesIO(blob), 'rb') as f:
        n = f.getnframes()
        if (f.getnchannels(), f.getsampwidth(), f.getframerate(), f.getcomptype()) != (1, 2, RATE, 'NONE') or not RATE <= n <= 90 * RATE:
            raise ValueError('require 1–90s PCM16 mono 48kHz')
        raw = f.readframes(n)
        if len(raw) != n * 2 or not any(raw):
            raise ValueError('truncated or silent PCM')
    return raw


def validate(script, assets, manifest):
    script, assets = Path(script), Path(assets).resolve()
    if not isinstance(manifest, dict) or manifest.get('schema') != 1 or manifest.get('locale') not in ('en-US', 'en-IN', 'hi-IN'):
        raise ValueError('unsupported manifest')
    basis = manifest.get('basis')
    if basis not in ('synthetic_fixture', 'owner_reviewed_recording', 'owner_reviewed_local_tts'):
        raise ValueError('unsupported narration basis')
    if basis != 'synthetic_fixture' and (manifest.get('rights_attested') is not True or manifest.get('listening_attested') is not True or not isinstance(manifest.get('rights_reference'), str) or not manifest['rights_reference'].strip()):
        raise ValueError('owner rights and listening declarations required')
    script_bytes = script.read_bytes()
    if manifest.get('script_sha256') != hashlib.sha256(script_bytes).hexdigest():
        raise ValueError('script hash mismatch')
    tokens = script_bytes.decode('utf-8').split()
    shots = manifest.get('shots')
    if not isinstance(shots, list) or len(shots) != 3 or not tokens or len(tokens) > 500:
        raise ValueError('three ordered shots required')
    cursor, frame, seen, records = 0, 0, set(), []
    for shot, visual in zip(shots, VISUALS):
        if not isinstance(shot, dict) or shot.get('visual') != visual or type(shot.get('word_start')) is not int or type(shot.get('word_end')) is not int:
            raise ValueError('invalid shot')
        a, b = shot['word_start'], shot['word_end']
        if a != cursor or not a < b <= len(tokens) or shot.get('text') != ' '.join(tokens[a:b]):
            raise ValueError('shot script coverage mismatch')
        name = shot.get('wav')
        if not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}\.wav', name) or name.lower() in seen:
            raise ValueError('unsafe or duplicate WAV name')
        seen.add(name.lower())
        path = assets / name
        if path.is_symlink() or not path.is_file() or path.resolve().parent != assets or path.stat().st_size > 9_000_000:
            raise ValueError('WAV path/hash mismatch')
        blob = path.read_bytes()
        if hashlib.sha256(blob).hexdigest() != shot.get('wav_sha256'):
            raise ValueError('WAV hash mismatch')
        raw = read_voice(blob)
        n = len(raw)//2; frames = math.ceil(n/SAMPLES)
        records.append(dict(visual=visual, word_start=a, word_end=b, start_frame=frame, end_frame=frame+frames, samples=n, padding_samples=frames*SAMPLES-n, wav_sha256=shot['wav_sha256'], raw=raw))
        cursor, frame = b, frame+frames
    if cursor != len(tokens):
        raise ValueError('incomplete script coverage')
    return records


def board(visual, font):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new('RGB', (W,H), '#0b1829'); d = ImageDraw.Draw(im)
    fs = {n:ImageFont.truetype(str(font), n) for n in (28,40,58,84,110)}
    white, cyan, amber, muted, panel = '#eef5ff', '#70e1d1', '#ffc368', '#a5b6cb', '#182f46'
    def txt(x,y,s,n=40,c=white):
        if d.textlength(s,font=fs[n])>W-x-65: raise ValueError('layout overflow')
        d.text((x,y),s,font=fs[n],fill=c)
    d.rectangle((0,0,W,10),fill=cyan); txt(90,55,'VIRALOS  /  SHA-256 LAB',28,cyan)
    title = {'file':'Would you notice one change?', 'compare':'Same length. Different bytes.', 'fingerprint':'Make the invisible visible.'}[visual]
    txt(90,130,title,84)
    if visual=='file':
        for x,label,content,c in [(110,'ORIGINAL FILE','hello',cyan),(990,'CHANGED FILE','Hello',amber)]:
            d.rounded_rectangle((x,305,x+820,705),36,fill=panel,outline=c,width=4);txt(x+55,350,label,40,c);txt(x+55,470,content,110);txt(x+55,620,'5 bytes',40,muted)
    elif visual=='compare':
        for j,(label,values,c) in enumerate([('hello','68 65 6c 6c 6f',cyan),('Hello','48 65 6c 6c 6f',amber)]):
            y=310+j*225;d.rounded_rectangle((110,y,1810,y+190),30,fill=panel);txt(165,y+40,label,84,c);txt(600,y+55,values,58)
        txt(110,800,'Hexadecimal byte values, calculated from UTF-8.',40,muted)
    else:
        for x,label,c in [(110,'INPUT',cyan),(735,'SHA-256',white),(1360,'256 BITS',amber)]:
            d.rounded_rectangle((x,370,x+450,610),30,fill=panel,outline=c,width=4);txt(x+35,440,label,58,c)
        for x in (575,1200):
            d.line((x,490,x+130,490),fill=muted,width=8);d.polygon([(x+130,470),(x+160,490),(x+130,510)],fill=muted)
        txt(110,730,'A fingerprint is not a proof of origin.',40,muted)
    d.rounded_rectangle((110,909,1810,922),6,fill='#334b61');txt(110,980,'TECHNICAL PREVIEW  /  NOT FOR PUBLICATION',28,muted)
    return im


def render(script, assets, manifest_path, output, font):
    from PIL import Image, ImageDraw
    started=time.monotonic(); manifest_path=Path(manifest_path); manifest_bytes=manifest_path.read_bytes(); manifest=json.loads(manifest_bytes); records=validate(script,assets,manifest)
    output=Path(output).resolve();output.mkdir(exist_ok=False);(output/'INCOMPLETE').touch();work=output/'work';work.mkdir()
    marker=Image.new('RGBA',(38,38));ImageDraw.Draw(marker).ellipse((1,1,36,36),fill='#70e1d1',outline='white',width=2);marker.save(work/'marker.png')
    focus=Image.new('RGBA',(78,78));fd=ImageDraw.Draw(focus);fd.ellipse((4,4,73,73),outline='#ffc368',width=6);fd.ellipse((30,30,47,47),fill='#ffc368');focus.save(work/'focus.png')
    with wave.open(str(work/'narration.wav'),'wb') as voice:
        voice.setparams((1,2,RATE,0,'NONE','not compressed'))
        for i,r in enumerate(records):
            n=r['end_frame']-r['start_frame']; voice.writeframes(r['raw']+b'\0'*(2*r['padding_samples']));board(r['visual'],font).save(work/f'{i}.png')
            # A continuous moving playhead, distinct animated shot entrance, and exact narration segment cuts.
            p=f'min(1,t/{max(.1,n/FPS)})'; x,y={'file':(f'230+880*{p}','545'),'compare':('590',f'365+225*{p}'),'fingerprint':(f'320+1250*{p}','450')}[r['visual']]
            filt=f"[0:v]format=yuv420p,fade=t=in:st=0:d=0.22[bg];[bg][1:v]overlay=x='110+1662*min(1,n/{max(1,n-1)})':y=896:eval=frame[progress];[progress][2:v]overlay=x='{x}':y='{y}':eval=frame,format=yuv420p"
            run('ffmpeg','-v','error','-nostdin','-loop','1','-framerate',str(FPS),'-i',str(work/f'{i}.png'),'-loop','1','-framerate',str(FPS),'-i',str(work/'marker.png'),'-loop','1','-framerate',str(FPS),'-i',str(work/'focus.png'),'-filter_complex_threads','2','-filter_complex',filt,'-frames:v',str(n),'-an','-c:v','libx264','-preset','ultrafast','-crf','21','-threads','4',str(work/f'{i}.mp4'))
    (work/'concat.txt').write_text('\n'.join(f"file '{i}.mp4'" for i in range(3))+'\n',encoding='utf-8')
    dest=output/'motion_preview.mp4';run('ffmpeg','-v','error','-nostdin','-f','concat','-safe','1','-i',str(work/'concat.txt'),'-i',str(work/'narration.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','160k','-movflags','+faststart',str(dest))
    run('ffmpeg','-v','error','-xerror','-nostdin','-threads','4','-i',str(dest),'-f','null','-')
    probe=json.loads(run('ffprobe','-v','error','-show_streams','-of','json',str(dest)).stdout);v=next(s for s in probe['streams'] if s['codec_type']=='video');a=next(s for s in probe['streams'] if s['codec_type']=='audio');expected=records[-1]['end_frame']/FPS
    if (v['width'],v['height'],v['avg_frame_rate'])!=(W,H,'30/1') or int(v['nb_frames'])!=records[-1]['end_frame'] or any(abs(float(s['duration'])-expected)>0.06 for s in (v,a)): raise ValueError('media timing mismatch')
    report=dict(status='TECHNICAL_PREVIEW_ONLY',publication_authorized=False,locale=manifest['locale'],basis=manifest['basis'],script_sha256=manifest['script_sha256'],manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),duration_s=expected,video_sha256=sha(dest),width=W,height=H,fps=FPS,decode_pass=True,acoustic_alignment_verified=False,rights_verified=False,visual_scope='English SHA-256 chapter-one-specific artwork, animated focus markers, playhead and shot fades',shots=[{k:v for k,v in r.items() if k!='raw'} for r in records],elapsed_s=round(time.monotonic()-started,2))
    (output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');(output/'INCOMPLETE').unlink();return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('script','assets','manifest','output','font'): p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(render(a.script,a.assets,a.manifest,a.output,a.font),indent=2))
