"""Offline source-linked SHA-256 long-form synthetic rough cut; no release authority."""
import argparse, hashlib, json, math, subprocess, time, wave
from pathlib import Path
from urllib.parse import urlparse
W,H,FPS=1920,1080,30
DIGESTS=[hashlib.sha256(x).hexdigest() for x in (b'hello',b'Hello')]
BITS=[bool((int(DIGESTS[0],16)^int(DIGESTS[1],16))>>(255-i)&1) for i in range(256)]

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def validate(p):
    if p.get('schema')!=1 or p.get('status')!='DRAFT_SYNTHETIC_ONLY' or p.get('locale')!='en-US' or p.get('target_minutes')!=[6,8]: raise ValueError('synthetic English draft only')
    sources=p.get('sources'); scenes=p.get('scenes')
    if not isinstance(sources,dict) or not sources or any(not isinstance(v,str) or urlparse(v).scheme!='https' or not urlparse(v).hostname for v in sources.values()): raise ValueError('source references required')
    if not isinstance(scenes,list) or not 6<=len(scenes)<=12: raise ValueError('scene count')
    words=0
    for i,s in enumerate(scenes,1):
        if not isinstance(s,dict) or s.get('id')!=f'{i:02}' or s.get('layout') not in ('compare','flow','code','bits'): raise ValueError('scene order/layout')
        t,n,b,r=(s.get(k) for k in ('title','narration','beats','sources'))
        if not isinstance(t,str) or not 1<=len(t)<=44 or not isinstance(n,str) or not 55<=len(n.split())<=180: raise ValueError('narration/title')
        if not isinstance(b,list) or len(b)!=3 or any(not isinstance(x,str) or not 1<=len(x)<=60 for x in b): raise ValueError('three visual beats')
        if not isinstance(r,list) or not r or any(not isinstance(x,str) or x not in sources for x in r): raise ValueError('unknown source')
        if any(not 32<=ord(c)<=126 for c in t+n+''.join(b)): raise ValueError('printable ASCII only')
        words+=len(n.split())
    if not 780<=words<=1200: raise ValueError('long-form word budget')
    return words

def run(*args,timeout=300): return subprocess.run(args,check=True,capture_output=True,text=True,timeout=timeout)
def stamp(ms): return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'

def board(s,beat,total,font):
    from PIL import Image,ImageDraw,ImageFont
    im=Image.new('RGB',(W,H),'#101b2c');d=ImageDraw.Draw(im)
    fs={n:ImageFont.truetype(str(font),n) for n in (28,34,44,52,72,116)}
    white='#ecf5ff';cyan='#6de2cf';amber='#ffbf6b';muted='#9caec3';panel='#20354b'
    def txt(x,y,t,n=44,c=white):
        if d.textlength(t,font=fs[n])>W-x-65: raise ValueError('visual overflow: '+t)
        d.text((x,y),t,font=fs[n],fill=c)
    d.rectangle((0,0,W,10),fill=cyan);txt(80,52,f'VIRALOS  /  SHA-256 LAB  /  CHAPTER {s["id"]} OF {total:02}',28,cyan);txt(80,115,s['title'],72);d.line((80,235,1840,235),fill='#30485e',width=3)
    if s['layout']=='bits':
        for k,b in enumerate(BITS):
            x=85+k%32*35;y=305+k//32*49
            d.rounded_rectangle((x,y,x+26,y+35),6,fill=(amber if b else cyan) if beat>=1 else panel)
        txt(1250,330,'256' if beat==0 else str(sum(BITS)),116,amber if beat else cyan);txt(1250,485,'output bits' if beat==0 else 'changed bits',44);txt(85,770,'Amber = different  /  Teal = same',34,muted)
    elif s['layout']=='code':
        for j,(name,digest) in enumerate(zip(('hello','Hello'),DIGESTS)):
            y=285+j*255;d.rounded_rectangle((80,y,1840,y+220),25,fill=panel);txt(112,y+20,f"hashlib.sha256(b'{name}').hexdigest()",44,cyan if j==0 else amber)
            if beat>=j+1: txt(112,y+95,digest[:32],44);txt(112,y+150,digest[32:],44)
    else:
        for j,b in enumerate(s['beats']):
            y=288+j*175;active=j==beat;d.rounded_rectangle((80,y,1840,y+145),22,fill=panel,outline=cyan if active else '#354d64',width=4);txt(112,y+36,f'{j+1:02}',44,cyan if active else muted);txt(245,y+33,b,52,white if active else muted)
    txt(85,895,s['beats'][beat],34,cyan);txt(85,990,'SYNTHETIC ROUGH CUT  /  NOT FOR PUBLICATION',28,muted)
    for j in range(3): d.rectangle((1500+j*115,1000,1595+j*115,1008),fill=cyan if j<=beat else panel)
    return im

def prepare(plan_path,output,font,espeak='espeak'):
    plan_path,output=Path(plan_path),Path(output);p=json.loads(plan_path.read_text(encoding='utf-8'));words=validate(p)
    output.mkdir(exist_ok=False);(output/'INCOMPLETE').touch();work=output/'work';work.mkdir();concat=[];chapters=[];clock=0;captions=['WEBVTT','']
    with wave.open(str(work/'voice.wav'),'wb') as voice:
        voice.setparams((1,2,48000,0,'NONE','not compressed'))
        for i,s in enumerate(p['scenes']):
            wav=work/f'{i:02}.wav';pcm=work/f'{i:02}.pcm';run(espeak,'-v','en-us','-s','155','-w',str(wav),s['narration']);run('ffmpeg','-v','error','-nostdin','-i',str(wav),'-ac','1','-ar','48000','-f','s16le',str(pcm));raw=pcm.read_bytes();units=math.ceil(len(raw)/19200)+1
            if units<3: raise ValueError('short scene')
            voice.writeframes(raw+b'\0'*(units*19200-len(raw)));counts=[units//3,units//3,units-2*(units//3)]
            for b,count in enumerate(counts):
                name=f'{i:02}-{b}.png';board(s,b,len(p['scenes']),font).save(work/name);concat.extend([f"file '{name}'",f'duration {count/5:.1f}'])
            end=clock+units*200;chapters.append({'id':s['id'],'title':s['title'],'start_ms':clock,'end_ms':end,'sources':s['sources']});captions.extend([f'{stamp(clock)} --> {stamp(end)}',s['narration'],'']);clock=end;wav.unlink();pcm.unlink()
    if not 360000<=clock<=480000: raise ValueError(f'actual duration outside 6–8 minutes: {clock} ms')
    concat.append(f"file '{len(p['scenes'])-1:02}-2.png'");(work/'frames.ffconcat').write_text('ffconcat version 1.0\n'+'\n'.join(concat)+'\n',encoding='utf-8')
    (output/'scene_transcript.vtt').write_text('\n'.join(captions)+'\n',encoding='utf-8');(output/'chapters.json').write_text(json.dumps(chapters,indent=2)+'\n',encoding='utf-8');board(p['scenes'][3],2,len(p['scenes']),font).resize((1280,720)).save(output/'thumbnail_draft.png')
    return {'plan_sha256':sha(plan_path),'duration_s':clock/1000,'words':words,'chapters':chapters,'visual_beats':len(chapters)*3}

def render(plan_path,output,font,espeak='espeak'):
    start=time.monotonic();output=Path(output);r=prepare(plan_path,output,font,espeak);work=output/'work';dest=output/'rough_cut.mp4'
    run('ffmpeg','-v','error','-nostdin','-f','concat','-safe','1','-i',str(work/'frames.ffconcat'),'-i',str(work/'voice.wav'),'-map','0:v:0','-map','1:a:0','-vf','fps=30,format=yuv420p','-t',str(r['duration_s']),'-c:v','libx264','-preset','ultrafast','-threads','4','-crf','24','-c:a','aac','-b:a','160k','-movflags','+faststart',str(dest),timeout=420)
    run('ffmpeg','-v','error','-xerror','-nostdin','-threads','4','-i',str(dest),'-f','null','-',timeout=300)
    probe=json.loads(run('ffprobe','-v','error','-show_streams','-of','json',str(dest)).stdout);v=next(x for x in probe['streams'] if x['codec_type']=='video');a=next(x for x in probe['streams'] if x['codec_type']=='audio')
    if (v['width'],v['height'],v['avg_frame_rate'])!=(W,H,'30/1') or abs(float(v['duration'])-r['duration_s'])>.1 or abs(float(a['duration'])-r['duration_s'])>.1: raise ValueError('media mismatch')
    r.update(status='SYNTHETIC_ROUGH_CUT_ONLY',publication_authorized=False,video_sha256=sha(dest),width=W,height=H,fps=FPS,caption_basis='scene transcript only; not word aligned',visual_basis='progressive static compositions and cuts; no continuous motion',voice_basis='synthetic eSpeak English only',experiment={'hashes':DIGESTS,'changed_bits':sum(BITS)},decode_pass=True,elapsed_s=round(time.monotonic()-start,2));(output/'receipt.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');(output/'INCOMPLETE').unlink();return r

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--font',type=Path,required=True);p.add_argument('--espeak',default='espeak');a=p.parse_args();print(json.dumps(render(a.plan,a.output,a.font,a.espeak),indent=2))
