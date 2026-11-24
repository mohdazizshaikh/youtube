"""Private full Hindi review render and English owner narration intake. No release authority."""
import argparse, io, json, math, re, subprocess, time, wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
try:
    from . import phase14_localize as loc, phase14_quality as q
except ImportError:
    import phase14_localize as loc, phase14_quality as q

def pin(s):
    if not isinstance(s,str) or not re.fullmatch(r'[0-9a-f]{64}',s): raise ValueError('exact SHA256 required')
    return s

def dump(path,obj):
    with Path(path).open('x',encoding='utf8') as f: json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')

def prepared(plan,folder,expected):
    folder=Path(folder);p,pp=loc.load_plan(plan);raw=loc.read(folder/'receipt.json',100000);r=json.loads(raw)
    if (folder/'INCOMPLETE').exists() or loc.digest(raw)!=pin(expected) or r.get('schema')!='VIRALOS_HINDI_INTAKE_V1' or r.get('locale')!='hi-IN' or r.get('basis')!='synthetic_espeak' or r.get('plan_sha256')!=pp or r.get('publication_authorized') is not False: raise ValueError('prepared synthetic identity mismatch')
    if len(r.get('shots',[]))!=24 or len(r.get('board_sha256',[]))!=24: raise ValueError('24 ordered shots required')
    cursor=0
    for i,s in enumerate(r['shots']):
        n=s['samples'];pin(s['wav_sha256']);pin(r['board_sha256'][i])
        if type(n) is not int or not 48000<=n<=4320000: raise ValueError('sample bound')
        f=(n+1599)//1600
        if s['chapter']!=f'{i//3+1:02}' or s['beat']!=i%3 or s['start_frame']!=cursor or s['end_frame']!=cursor+f or s['padding_samples']!=f*1600-n: raise ValueError('timeline mismatch')
        cursor+=f
    if type(r['frames']) is not int or r['frames']!=cursor or not 720<=cursor<=27000 or not math.isclose(r['duration_seconds'],cursor/30,abs_tol=1e-8): raise ValueError('duration mismatch')
    wav=loc.read(folder/'narration.wav',90_000_000)
    if loc.digest(wav)!=pin(r['narration_sha256']): raise ValueError('audio mismatch')
    with wave.open(io.BytesIO(wav),'rb') as w:
        if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes(),w.getcomptype())!=(1,2,48000,cursor*1600,'NONE'): raise ValueError('PCM mismatch')
        for s in r['shots']:
            b=w.readframes(s['samples']);padding=w.readframes(s['padding_samples'])
            if len(b)!=s['samples']*2 or not any(b) or padding!=b'\0'*(s['padding_samples']*2): raise ValueError('PCM padding mismatch')
    return p,r,wav

def cues(text,samples,font):
    words=text.split(); end=samples//480
    if not words or end<4*len(words) or any(any(c in w for c in '{}\\<>') or any(ord(c)<32 for c in w) for w in words): raise ValueError('invalid fixture tokens/timing')
    groups=[];group=[]
    for w in words:
        if font.getlength(w)>1580: raise ValueError('caption overflow')
        if group and (len(group)==4 or font.getlength(' '.join(group+[w]))>1580): groups.append(group);group=[]
        group.append(w)
    if group:groups.append(group)
    out=[];i=0
    for g in groups:
        for j,w in enumerate(g):
            out.append(dict(text=w,start=end*i//len(words),end=end*(i+1)//len(words),group=g,active=j));i+=1
    return out

def clock(cs):return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'
def ass(rows,frames,family):
    if not re.fullmatch(r'[A-Za-z0-9 _-]{1,60}',family):raise ValueError('invalid font family')
    h=f'''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{family},55,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,2,100,100,15,1
Style: Warning,DejaVu Sans,29,&H0087DFFF,&H0087DFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,8,20,20,925,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines=[f'Dialogue: 1,0:00:00.00,{clock(math.ceil(frames*100/30))},Warning,,0,0,0,,SYNTHETIC HINDI / WORD TIMING NOT ALIGNED / NO RELEASE']
    for c in rows:
        text=' '.join(r'{\c&H0087DFFF&}'+w+r'{\c&H00FFFFFF&}' if j==c['active'] else w for j,w in enumerate(c['group']))
        lines.append(f"Dialogue: 0,{clock(c['start'])},{clock(c['end'])},Caption,,0,0,0,,{text}")
    return h+'\n'.join(lines)+'\n'

def audit(video,frames):
    ss=json.loads(loc.run('ffprobe','-v','error','-show_streams','-of','json',str(video)).stdout)['streams']
    if len(ss)!=2 or {s['codec_type'] for s in ss}!={'video','audio'}:raise ValueError('stream count')
    v=next(s for s in ss if s['codec_type']=='video');a=next(s for s in ss if s['codec_type']=='audio')
    if (v['codec_name'],v['width'],v['height'],v['avg_frame_rate'],int(v['nb_frames']),v['pix_fmt'])!=('h264',1920,1080,'30/1',frames,'yuv420p') or (a['codec_name'],a['sample_rate'],a['channels'])!=('aac','48000',1):raise ValueError('stream format')
    for s in (v,a):
        d=float(s['duration']);st=float(s.get('start_time','nan'))
        if not math.isfinite(d) or not math.isfinite(st) or abs(d-frames/30)>.06 or abs(st)>.04:raise ValueError('stream timing')
    loc.run('ffmpeg','-v','error','-xerror','-nostdin','-i',str(video),'-f','null','-',timeout=300)
    loud=q.measure(video);return dict(video_sha256=q.sha(video),frames=frames,duration_seconds=frames/30,video_duration_seconds=float(v['duration']),audio_duration_seconds=float(a['duration']),decode_pass=True,loudness=loud,numeric_audio_gate_pass=q.accepted(loud),publication_authorized=False)

def render(plan,folder,expected,output,fontpath,latinfont):
    p,r,wav=prepared(plan,folder,expected);out=Path(output).resolve();out.mkdir(exist_ok=False);(out/'INCOMPLETE').touch();work=out/'work';work.mkdir();start=time.monotonic();(work/'narration.wav').write_bytes(wav)
    font=loc.font(fontpath,55);records=[];words=[]
    for i,s in enumerate(r['shots']):
        b=io.BytesIO();loc.board(p['chapters'][i//3],i%3,fontpath,latinfont).save(b,format='PNG');data=b.getvalue()
        if loc.digest(data)!=r['board_sha256'][i]:raise ValueError('board regeneration mismatch; use original font/runtime')
        (work/f'{i:02}.png').write_bytes(data);rows=cues(p['chapters'][i//3]['segments'][i%3],s['samples'],font);n=s['end_frame']-s['start_frame']
        (work/f'{i:02}.ass').write_text(ass(rows,n,font.getname()[0]),encoding='utf8');records.append((i,n))
        for c in rows:words.append(dict(shot=i,text=c['text'],start_ms=s['start_frame']*1000/30+c['start']*10,end_ms=s['start_frame']*1000/30+c['end']*10))
    def shot(pair):
        i,n=pair;f=f'{i:02}';vf=f'scale=1632:918:flags=lanczos,pad=1920:1080:144:0:color=0x101f32,ass={f}.ass'
        subprocess.run(['ffmpeg','-v','error','-nostdin','-n','-loop','1','-framerate','30','-i',f+'.png','-vf',vf,'-frames:v',str(n),'-an','-c:v','libx264','-threads','2','-filter_threads','1','-preset','ultrafast','-crf','23','-pix_fmt','yuv420p',f+'.mp4'],cwd=work,check=True,timeout=180,capture_output=True)
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(shot,records))
    (work/'concat.txt').write_text(''.join(f"file '{i:02}.mp4'\n" for i,_ in records),encoding='ascii');raw=out/'hindi_review.mp4'
    loc.run('ffmpeg','-v','error','-nostdin','-n','-f','concat','-safe','1','-i',str(work/'concat.txt'),'-i',str(work/'narration.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','160k','-movflags','+faststart',str(raw))
    report=audit(raw,r['frames']);report.update(schema='VIRALOS_HINDI_REVIEW_V1',locale='hi-IN',basis='synthetic_espeak',caption_basis='synthetic_fixture',plan_sha256=r['plan_sha256'],intake_receipt_sha256=expected,narration_sha256=r['narration_sha256'],words=len(words),shots=24,acoustic_alignment_verified=False,natural_voice_verified=False,elapsed_seconds=round(time.monotonic()-start,2),human_review_required=True)
    dump(out/'words.json',words);dump(out/'receipt.json',report);(out/'INCOMPLETE').unlink();return report

def english_request(plan,output):
    raw=loc.read(plan,100000);p=json.loads(raw)
    if loc.digest(raw)!=loc.PIN or p.get('locale')!='en-US' or len(p.get('scenes',[]))!=8:raise ValueError('pinned English plan required')
    out=Path(output);out.mkdir(exist_ok=False);(out/'INCOMPLETE').touch();(out/'scripts').mkdir();(out/'assets').mkdir();rows=[]
    for i,c in enumerate(p['scenes']):
        n=f'{i:02}';t=c['narration'];(out/'scripts'/f'{n}.txt').write_bytes(t.encode('utf8'));rows.append(dict(file=f'{n}.wav',script_sha256=loc.digest(t.encode('utf8')),wav_sha256=None))
    dump(out/'manifest.template.json',dict(schema='VIRALOS_ENGLISH_CHAPTER_INTAKE_V1',locale='en-US',basis='owner_reviewed_recording',plan_sha256=loc.PIN,rights_attested=False,listening_attested=False,rights_reference='',chapters=rows));(out/'INSTRUCTIONS.txt').write_text('Record eight exact chapter scripts, mono PCM16 48kHz, 1–90s each. Complete actual WAV hashes and private rights/listening declarations after review. New acoustic segmentation and re-render required; never reuse synthetic timings. No release authority.\n');(out/'INCOMPLETE').unlink()

def english_intake(plan,manifest,assets):
    raw=loc.read(plan,100000);p=json.loads(raw);m=json.loads(loc.read(manifest,100000))
    if loc.digest(raw)!=loc.PIN or m.get('plan_sha256')!=loc.PIN or m.get('schema')!='VIRALOS_ENGLISH_CHAPTER_INTAKE_V1' or m.get('locale')!='en-US' or m.get('basis') not in ('owner_reviewed_recording','owner_reviewed_local_tts') or m.get('rights_attested') is not True or m.get('listening_attested') is not True or not isinstance(m.get('rights_reference'),str) or not m['rights_reference'].strip():raise ValueError('owner manifest incomplete')
    rows=m.get('chapters');assets=Path(assets)
    if not isinstance(rows,list) or len(rows)!=8 or assets.is_symlink() or not assets.is_dir():raise ValueError('eight private chapters required')
    records=[]
    for i,(c,row) in enumerate(zip(p['scenes'],rows)):
        name=f'{i:02}.wav'
        if row.get('file')!=name or row.get('script_sha256')!=loc.digest(c['narration'].encode('utf8')):raise ValueError('chapter mismatch')
        data=loc.read(assets/name,9_000_000)
        if loc.digest(data)!=pin(row.get('wav_sha256')):raise ValueError('WAV mismatch')
        _,samples=loc.pcm(data);records.append(dict(chapter=i+1,samples=samples,wav_sha256=row['wav_sha256']))
    return dict(chapters=records,plan_sha256=loc.PIN,natural_voice_verified=False,acoustic_alignment_verified=False,publication_authorized=False)

def bind_metadata(draft,hi_plan,folder,expected,raw_video,render_receipt,mastered,master_receipt,output):
    p,r,_=prepared(hi_plan,folder,expected);m=json.loads(loc.read(draft,100000));v=json.loads(loc.read(render_receipt,100000));a=json.loads(loc.read(master_receipt,100000))
    if m.get('schema')!='VIRALOS_PACKAGING_DRAFT_V1' or m.get('publication_authorized') is not False or m.get('hindi_plan_sha256')!=r['plan_sha256'] or m['hindi']['chapters'] is not None or m['hindi']['video_sha256'] is not None:raise ValueError('draft metadata mismatch')
    if v.get('schema')!='VIRALOS_HINDI_REVIEW_V1' or v.get('intake_receipt_sha256')!=expected or v.get('plan_sha256')!=r['plan_sha256'] or v.get('frames')!=r['frames'] or v.get('publication_authorized') is not False or v.get('video_sha256')!=q.sha(raw_video):raise ValueError('render mismatch')
    final=audit(mastered,r['frames'])
    if a.get('source_sha256')!=v['video_sha256'] or a.get('output_sha256')!=final['video_sha256'] or a.get('publication_authorized') is not False or a.get('numeric_gate_pass') is not True or not final['numeric_audio_gate_pass']:raise ValueError('master chain failed')
    chapters=[dict(start_seconds=r['shots'][i*3]['start_frame']//30,title=c['title']) for i,c in enumerate(p['chapters'])]
    if any(b['start_seconds']-a['start_seconds']<10 for a,b in zip(chapters,chapters[1:])) or r['frames']/30-chapters[-1]['start_seconds']<10:raise ValueError('chapter too short')
    m['hindi'].update(chapters=chapters,video_sha256=final['video_sha256'],caption_basis='synthetic_fixture',duration_seconds=r['frames']/30);m['schema']='VIRALOS_PACKAGING_DRAFT_V2';m['hindi_technical_audit']=final;m['human_review_required']=True;dump(output,m);return m

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    for cmd,args in [('render','plan folder expected output fontpath latinfont'),('english-request','plan output'),('english-intake','plan manifest assets'),('bind-metadata','draft hi_plan folder expected raw_video render_receipt mastered master_receipt output')]:
        s=sub.add_parser(cmd)
        for k in args.split():s.add_argument('--'+k.replace('_','-'),required=True,type=str if k=='expected' else Path)
    a=vars(p.parse_args());cmd=a.pop('cmd');print(json.dumps({'render':render,'english-request':english_request,'english-intake':english_intake,'bind-metadata':bind_metadata}[cmd](**a),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
