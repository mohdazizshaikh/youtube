"""Offline full-film motion assembly and fresh technical audit; synthetic only."""
import argparse
import hashlib
import json
import math
import re
import time
import wave
from pathlib import Path
try:
    from . import phase14_film as film, phase14_motion as motion, phase14_quality as quality
except ImportError:
    import phase14_film as film, phase14_motion as motion, phase14_quality as quality

W,H,FPS,RATE=1920,1080,30,48000
SAMPLES=RATE//FPS
# Manually selected sentence boundaries for the pinned original English plan.
CUTS=((4,7),(3,6),(3,6),(3,5),(2,5),(2,5),(2,5),(5,8))
PLAN_SHA='eb5a7ef2df3f371cad4b9c51d8275df5f6e3bf0ee59f8b28f6e8f5b7318c1e54'

def segments(plan):
    film.validate(plan)
    if len(plan['scenes'])!=8: raise ValueError('eight chapters required')
    result=[]
    for scene,(a,b) in zip(plan['scenes'],CUTS):
        sentences=re.split(r'(?<=[.!?]) +',scene['narration'])
        if not 0<a<b<len(sentences): raise ValueError('invalid sentence boundaries')
        parts=[' '.join(sentences[x:y]) for x,y in ((0,a),(a,b),(b,len(sentences)))]
        if ' '.join(parts)!=scene['narration'] or any(not p.strip() for p in parts): raise ValueError('script coverage mismatch')
        result.extend(dict(chapter=scene['id'],beat=i,text=p,scene=scene) for i,p in enumerate(parts))
    return result

def timeline(raw_lengths):
    if len(raw_lengths)!=24 or any(type(n) is not int or not RATE<=n<=90*RATE for n in raw_lengths): raise ValueError('invalid PCM lengths')
    out=[]; cursor=0
    for i,n in enumerate(raw_lengths):
        frames=(n+SAMPLES-1)//SAMPLES
        out.append(dict(chapter=f'{i//3+1:02}',beat=i%3,start_frame=cursor,end_frame=cursor+frames,samples=n,padding_samples=frames*SAMPLES-n))
        cursor+=frames
    if not 360*FPS<=cursor<=480*FPS: raise ValueError('film duration outside 6–8 minutes')
    return out

def check_timeline(records):
    if not isinstance(records,list) or len(records)!=24: raise ValueError('24 shots required')
    if any(not isinstance(r,dict) or 'samples' not in r for r in records): raise ValueError('invalid shot records')
    expected=timeline([r['samples'] for r in records])
    if records!=expected: raise ValueError('timeline mismatch')
    return expected[-1]['end_frame']

def audit(video, expected_sha, records, require_mastered=False):
    video=Path(video).resolve()
    if not re.fullmatch(r'[a-f0-9]{64}',expected_sha) or film.sha(video)!=expected_sha: raise ValueError('video hash mismatch')
    count=check_timeline(records); duration=count/FPS
    p=json.loads(film.run('ffprobe','-v','error','-show_streams','-of','json',str(video)).stdout)
    streams=p['streams']; v=[s for s in streams if s['codec_type']=='video']; a=[s for s in streams if s['codec_type']=='audio']
    if len(streams)!=2 or len(v)!=1 or len(a)!=1: raise ValueError('unexpected stream inventory')
    v,a=v[0],a[0]
    if (v['codec_name'],v['width'],v['height'],v['avg_frame_rate'],v['pix_fmt'],int(v['nb_frames']))!=('h264',W,H,'30/1','yuv420p',count): raise ValueError('video format or frame count mismatch')
    if (a['codec_name'],a['sample_rate'],a['channels'])!=('aac','48000',1): raise ValueError('audio format mismatch')
    for s in (v,a):
        end,start=float(s['duration']),float(s.get('start_time',0))
        if not math.isfinite(end) or not math.isfinite(start) or abs(end-duration)>0.06 or abs(start)>0.06: raise ValueError('stream timing mismatch')
    film.run('ffmpeg','-v','error','-xerror','-nostdin','-threads','4','-i',str(video),'-map','0:v:0','-map','0:a:0','-f','null','-',timeout=300)
    m=quality.measure(video); passed=quality.accepted(m)
    if require_mastered and not passed: raise ValueError('numeric audio gate failed')
    if film.sha(video)!=expected_sha: raise ValueError('video changed during audit')
    return dict(status='TECHNICAL_AUDIT_ONLY',video_sha256=expected_sha,frames=count,duration_s=duration,video_stream_duration_s=float(v['duration']),audio_stream_duration_s=float(a['duration']),width=W,height=H,fps=FPS,decode_pass=True,loudness=m,numeric_audio_gate_pass=passed,publication_authorized=False,acoustic_alignment_verified=False,editorial_review_required=True)

def render(plan_path, output, font, espeak='espeak'):
    from PIL import Image,ImageDraw
    start=time.monotonic();plan_path=Path(plan_path); blob=plan_path.read_bytes()
    if hashlib.sha256(blob).hexdigest()!=PLAN_SHA: raise ValueError('pinned English plan required')
    plan=json.loads(blob); shots=segments(plan);output=Path(output).resolve();output.mkdir(exist_ok=False);(output/'INCOMPLETE').touch();work=output/'work';work.mkdir()
    lengths=[]
    for i,s in enumerate(shots):
        wav=work/f'{i:02}.wav';raw=work/f'{i:02}.pcm'
        film.run(espeak,'-v','en-us','-s','155','-w',str(wav),s['text'])
        film.run('ffmpeg','-v','error','-nostdin','-i',str(wav),'-ac','1','-ar','48000','-f','s16le',str(raw));wav.unlink(); size=raw.stat().st_size
        if size%2: raise ValueError('invalid PCM bytes')
        lengths.append(size//2)
    records=timeline(lengths)
    marker=Image.new('RGBA',(38,38));ImageDraw.Draw(marker).ellipse((1,1,36,36),fill='#70e1d1',outline='white',width=2);marker.save(work/'marker.png')
    focus=Image.new('RGBA',(78,78));d=ImageDraw.Draw(focus);d.ellipse((4,4,73,73),outline='#ffc368',width=6);d.ellipse((30,30,47,47),fill='#ffc368');focus.save(work/'focus.png')
    with wave.open(str(work/'narration.wav'),'wb') as voice:
        voice.setparams((1,2,RATE,0,'NONE','not compressed'))
        for i,(s,r) in enumerate(zip(shots,records)):
            raw=work/f'{i:02}.pcm';data=raw.read_bytes()
            if len(data)!=2*r['samples'] or not any(data): raise ValueError('PCM mismatch or silence')
            voice.writeframes(data+b'\0'*(2*r['padding_samples']));raw.unlink();n=r['end_frame']-r['start_frame'];b=s['beat'];scene=s['scene']
            # Chapter 1 uses Phase 14D original artwork. Others reuse Phase 14C boards with animated markers/fades.
            board=motion.board(motion.VISUALS[b],font) if scene['id']=='01' else film.board(scene,b,8,font)
            board.save(work/f'{i:02}.png');p=f'min(1,t/{max(.1,n/FPS)})'
            if scene['id']=='01': x,y=[(f'230+880*{p}','545'),('590',f'365+225*{p}'),(f'320+1250*{p}','450')][b]
            elif scene['layout']=='bits': x,y=f'85+1030*{p}',str(305+49*(2+b))
            elif scene['layout']=='code': x,y=f'110+1530*{p}',str(270+255*min(1,b))
            else: x,y=f'120+1550*{p}',str(300+175*b)
            filt=f"[0:v]format=yuv420p,fade=t=in:st=0:d=0.18[bg];[bg][1:v]overlay=x='110+1662*min(1,n/{max(1,n-1)})':y=925:eval=frame[prog];[prog][2:v]overlay=x='{x}':y='{y}':eval=frame,format=yuv420p"
            film.run('ffmpeg','-v','error','-nostdin','-loop','1','-framerate','30','-i',str(work/f'{i:02}.png'),'-loop','1','-framerate','30','-i',str(work/'marker.png'),'-loop','1','-framerate','30','-i',str(work/'focus.png'),'-filter_complex_threads','2','-filter_complex',filt,'-frames:v',str(n),'-an','-c:v','libx264','-preset','ultrafast','-crf','22','-threads','4',str(work/f'{i:02}.mp4'))
    (work/'concat.txt').write_text('\n'.join(f"file '{i:02}.mp4'" for i in range(24))+'\n',encoding='utf-8')
    dest=output/'motion_film.mp4';film.run('ffmpeg','-v','error','-nostdin','-f','concat','-safe','1','-i',str(work/'concat.txt'),'-i',str(work/'narration.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','160k','-movflags','+faststart',str(dest))
    r=audit(dest,film.sha(dest),records);r.update(plan_sha256=PLAN_SHA,shots=records,visual_basis='animated markers and fades over original boards; not fully cinematic',voice_basis='synthetic eSpeak English',caption_basis='segment transcript only',elapsed_s=round(time.monotonic()-start,2))
    captions=['WEBVTT',''];chapters=[]
    for i,(s,rec) in enumerate(zip(shots,records)):
        captions.extend([f"{film.stamp(round(rec['start_frame']*1000/FPS))} --> {film.stamp(round(rec['end_frame']*1000/FPS))}",s['text'],''])
        if i%3==0: chapters.append(dict(id=s['chapter'],title=s['scene']['title'],start_frame=rec['start_frame'],end_frame=records[i+2]['end_frame']))
    (output/'segment_transcript.vtt').write_text('\n'.join(captions)+'\n',encoding='utf-8');(output/'chapters.json').write_text(json.dumps(chapters,indent=2)+'\n',encoding='utf-8');(output/'receipt.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');(output/'INCOMPLETE').unlink();return r

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    r=sub.add_parser('render');r.add_argument('--plan',type=Path,required=True);r.add_argument('--output',type=Path,required=True);r.add_argument('--font',type=Path,required=True);r.add_argument('--espeak',default='espeak')
    a=sub.add_parser('audit');a.add_argument('--video',type=Path,required=True);a.add_argument('--sha256',required=True);a.add_argument('--timeline',type=Path,required=True);a.add_argument('--require-mastered',action='store_true')
    args=p.parse_args();result=render(args.plan,args.output,args.font,args.espeak) if args.cmd=='render' else audit(args.video,args.sha256,json.loads(args.timeline.read_text(encoding='utf-8'))['shots'],args.require_mastered);print(json.dumps(result,indent=2))
