"""Bilingual eight-chapter diagram review film. Synthetic audio only, no release."""
import argparse, hashlib, json, math, subprocess, time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, features
try:
    from . import phase14_bilingual as b, phase14_scene_review as s
except ImportError:
    import phase14_bilingual as b, phase14_scene_review as s

PLAN={'en':'eb5a7ef2df3f371cad4b9c51d8275df5f6e3bf0ee59f8b28f6e8f5b7318c1e54','hi':'eaf1eefbe8b4ff920297a3adc9a2c289fdfe9adacd6e7f67dad69237d89042a9'}
A,H=[hashlib.sha256(x).hexdigest() for x in (b'hello',b'Hello')]
BITS=[int(x) for x in f'{int(A,16)^int(H,16):0256b}']; DIFFER=sum(BITS)
BG='#0b1829'; PANEL='#17334a'; TEAL='#65e0cf'; GOLD='#ffd36a'; WHITE='#f1f5f9'; MUTED='#a8c0d1'
LABELS={
'en':[['Download A','Download B','Same length, different bytes'],['Input bytes','SHA-256','Fixed 256-bit output'],['Compute','Repeat','Compare full digests'],['256 output bits','Different bits','Example only, not a security score'],['Trusted reference','Downloaded bytes','Compare all 64 hex digits'],['Hash fingerprint','Encryption with key','Different purposes'],['Matching bytes','Trusted origin','Signature verification is separate'],['Hash exact bytes','Compare trusted reference','Verify origin separately']],
'hi':[['डाउनलोड A','डाउनलोड B','लंबाई समान, बाइट अलग'],['इनपुट बाइट','SHA-256','निश्चित 256 बिट'],['गणना करें','फिर चलाएँ','पूरे डाइजेस्ट की तुलना'],['256 आउटपुट बिट','अलग बिट','केवल इस प्रयोग का परिणाम'],['विश्वसनीय संदर्भ','डाउनलोड की बाइट','सभी 64 हेक्स अंक मिलाएँ'],['हैश फ़िंगरप्रिंट','कुंजी से एन्क्रिप्शन','अलग उद्देश्य'],['बाइट का मिलान','विश्वसनीय स्रोत','हस्ताक्षर की अलग जाँच'],['सही बाइट का हैश','विश्वसनीय संदर्भ से मिलाएँ','स्रोत की अलग जाँच']]}

def validate_shots(t):
    rows=t['shots'];cursor=0
    if not isinstance(rows,list) or len(rows)!=24:raise ValueError('24 shots required')
    for i,r in enumerate(rows):
        n=r['samples']
        if type(n) is not int or not 48000<=n<=4320000:raise ValueError('sample bound')
        f=(n+1599)//1600
        if (r['chapter'],r['beat'],r['start_frame'],r['end_frame'],r['padding_samples'])!=(f'{i//3+1:02}',i%3,cursor,cursor+f,f*1600-n):raise ValueError('timeline mismatch')
        cursor+=f
    if type(t['frames']) is not int or cursor!=t['frames'] or not 720<=cursor<=27000 or t.get('publication_authorized') is not False:raise ValueError('frame or release mismatch')
    return rows,cursor

def inputs(locale,plan,video,timeline,timeline_sha,receipt,receipt_sha,master=None,master_sha=None):
    if locale not in PLAN:raise ValueError('locale')
    p=s.read(plan,PLAN[locale]);t=s.read(timeline,timeline_sha);r=s.read(receipt,receipt_sha);rows,frames=validate_shots(t)
    if t.get('plan_sha256')!=PLAN[locale]:raise ValueError('plan identity')
    if locale=='en':
        if master is not None or master_sha is not None or r.get('status')!='SYNTHETIC_PRIVATE_REVIEW_CANDIDATE' or r.get('caption_basis')!='synthetic_fixture' or r.get('timeline_sha256')!=timeline_sha or r.get('raw_source_sha256')!=t.get('video_sha256') or r['audit']['frames']!=frames:raise ValueError('English chain')
        pin=b.pin(r['audit']['video_sha256']);chap=p['scenes']
    else:
        m=s.read(master,master_sha)
        if t.get('basis')!='synthetic_espeak' or r.get('schema')!='VIRALOS_HINDI_REVIEW_V1' or r.get('basis')!='synthetic_espeak' or r.get('caption_basis')!='synthetic_fixture' or r.get('intake_receipt_sha256')!=timeline_sha or r.get('plan_sha256')!=PLAN[locale] or r['frames']!=frames or m.get('source_sha256')!=r.get('video_sha256') or m.get('numeric_gate_pass') is not True or m.get('publication_authorized') is not False:raise ValueError('Hindi chain')
        pin=b.pin(m['output_sha256']);chap=p['chapters']
    if r.get('publication_authorized') is not False or r.get('acoustic_alignment_verified') is not False or len(chap)!=8 or b.q.sha(video)!=pin:raise ValueError('source pin or review gate')
    return chap,rows,frames,pin

def fonts(path):
    if not features.check('raqm'):raise ValueError('RAQM required')
    return {n:ImageFont.truetype(str(path),n,layout_engine=ImageFont.Layout.RAQM) for n in (17,19,22,25,29,34,38)}

def frame(locale,chapter,beat,step,title,beat_text,fs):
    if locale not in PLAN or type(chapter) is not int or not 0<=chapter<8 or type(beat) is not int or not 0<=beat<3 or type(step) is not int or not 0<=step<12:raise ValueError('phase')
    im=Image.new('RGB',(960,540),BG);d=ImageDraw.Draw(im);labels=LABELS[locale][chapter];p=(step+1)/12
    def txt(x,y,v,size=25,color=WHITE,maxw=880):
        for n in sorted((n for n in fs if n<=size),reverse=True):
            if fs[n].getlength(v)<=maxw: d.text((x,y),v,font=fs[n],fill=color);return
        raise ValueError('text width exceeds safe area: '+v)
    def box(x,y,w,h,fill=PANEL,outline=None):d.rounded_rectangle((x,y,x+w,y+h),radius=10,fill=fill,outline=outline,width=3 if outline else 1)
    def arrow(x,y,z,color=TEAL):
        d.line((x,y,z,y),fill=color,width=5);d.polygon([(z,y),(z-13,y-9),(z-13,y+9)],fill=color)
    txt(38,18,f'SHA-256   /   {chapter+1:02}   /   {beat+1:02}',19,TEAL);txt(38,50,title,38);txt(38,106,beat_text,25,GOLD)
    active=min(2,beat);focus=GOLD
    if chapter==0:
        for i,v in enumerate(('hello','Hello')):
            y=172+i*116;txt(42,y+22,labels[i],22,maxw=195)
            for j,c in enumerate(v):
                x=245+j*127;box(x,y,112,82,outline=focus if j==min(4,int(p*5)) else None);txt(x+17,y+8,c,34,GOLD if i==1 and j==0 else TEAL);txt(x+60,y+40,f'{ord(c):02X}',19)
        txt(42,420,labels[2],25,GOLD)
    elif chapter==1:
        for j,w in enumerate((250,250,250)):
            x=38+j*316;box(x,185,w,190,outline=TEAL if j<=min(2,int(p*3)) else None);txt(x+16,206,labels[j],25,maxw=w-32)
            if j==0:
                for k in range(5):box(x+15+k*44,277,36,42,TEAL if k<int(p*5+1) else '#29455b')
            elif j==1:txt(x+23,280,'SHA-256',34,GOLD)
            else:txt(x+20,280,'256 bit',34,TEAL)
            if j<2:arrow(x+260,278,x+305)
        txt(42,420,'64 hex × 4 bit = 256 bit',29,GOLD)
    elif chapter==2:
        for j,(value,digest) in enumerate((('hello',A),('Hello',H))):
            y=166+j*123;box(38,y,884,111,outline=TEAL if j==min(1,int(p*2)) else None)
            txt(52,y+8,f"hashlib.sha256(b'{value}').hexdigest()",25,GOLD)
            k=min(64,int(p*80)); shown=digest[:k]+'·'*(64-k)
            txt(52,y+54,shown,19,maxw=850)
        txt(42,420,labels[2],25,TEAL)
    elif chapter==3:
        n=min(256,int(p*256));
        for j,bit in enumerate(BITS):
            x=44+j%32*27;y=164+j//32*28;box(x,y,21,22,GOLD if j<n and bit else TEAL if j<n else '#29455b')
        txt(42,402,f'{sum(BITS[:n])} / 256',34,GOLD);txt(280,415,labels[2],22,MUTED,maxw=630)
    elif chapter in (4,7):
        for j in range(3):
            y=163+j*91;on=j<=min(2,int(p*3));box(40,y,880,76,outline=TEAL if on else None)
            txt(60,y+18,f'{j+1:02}',29,GOLD if on else MUTED);txt(130,y+19,labels[j],29,WHITE if on else MUTED,maxw=750)
        if chapter==4:txt(42,450,'SHA-256  /  Get-FileHash',22,TEAL)
    else:
        for j in range(2):
            x=38+j*450;box(x,165,432,210,outline=TEAL if j==min(1,int(p*2)) else None);txt(x+20,184,labels[j],25,maxw=390)
            if chapter==5:
                txt(x+20,260,'hello → SHA-256' if j==0 else 'data ⇄ ciphertext',29,GOLD)
                txt(x+20,307,'256 bit' if j==0 else 'with the correct key',22,TEAL)
            else:
                txt(x+20,259,'hash = hash' if j==0 else 'trusted key',29,GOLD)
                txt(x+20,307,'MATCH' if j==0 else 'VERIFY',22,TEAL)
        txt(42,421,labels[2],25,GOLD)
    d.line((38,479,922,479),fill='#416077',width=2);txt(38,493,'SYNTHETIC NARRATION / SHOT-LEVEL VISUALS / NOT FOR RELEASE',17,GOLD)
    return im

def schedule(count):
    if type(count) is not int or count<30:raise ValueError('shot duration')
    return [((i+1)*count//12-i*count//12) for i in range(12)]

def payload(path):
    r=subprocess.run(['ffmpeg','-v','error','-nostdin','-i',str(path),'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-'],check=True,capture_output=True,timeout=120)
    value=r.stdout.decode('ascii').strip()
    if not value.startswith('SHA256='):raise ValueError('audio hash')
    return b.pin(value[7:])

def mux(visual,audio,dest):
    # Do not use -frames:v or -shortest during mux: they can truncate AAC packets.
    subprocess.run(['ffmpeg','-v','error','-nostdin','-xerror','-n','-i',str(visual),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-c','copy','-movflags','+faststart',str(dest)],check=True,timeout=120)

def render(locale,plan,video,timeline,timeline_sha,receipt,receipt_sha,font,output,master=None,master_sha=None):
    start=time.monotonic();video=Path(video).resolve(strict=True);chap,rows,frames,pin=inputs(locale,plan,video,timeline,timeline_sha,receipt,receipt_sha,master,master_sha);fs=fonts(font)
    out=Path(output).resolve();out.mkdir(exist_ok=False);(out/'INCOMPLETE').touch();work=out/'frames';work.mkdir()
    lines=['ffconcat version 1.0'];last=None
    for i,r in enumerate(rows):
        c=chap[i//3];n=r['end_frame']-r['start_frame']
        for j,f in enumerate(schedule(n)):
            name=f'{i:02d}-{j:02d}.png';frame(locale,i//3,i%3,j,c['title'],c['beats'][i%3],fs).save(work/name)
            last='frames/'+name;lines.extend([f"file '{last}'",'option framerate 30',f'duration {f/30:.12f}'])
    lines.extend([f"file '{last}'",'option framerate 30']);(out/'frames.ffconcat').write_text('\n'.join(lines)+'\n',encoding='ascii')
    dest=out/'semantic_review.mp4';silent=out/'visual_only.mp4'
    cmd=['ffmpeg','-v','error','-nostdin','-xerror','-n','-f','concat','-safe','0','-i','frames.ffconcat','-map','0:v:0','-an','-vf','fps=30,scale=1920:1080:flags=lanczos','-frames:v',str(frames),'-c:v','libx264','-threads','2','-filter_threads','1','-preset','ultrafast','-crf','23','-pix_fmt','yuv420p',str(silent)]
    subprocess.run(cmd,cwd=out,check=True,timeout=300)
    mux(silent,video,dest)
    audit=b.audit(dest,frames);original=payload(video);final=payload(dest)
    if original!=final or b.q.sha(video)!=pin:raise ValueError('audio payload or source changed')
    report=dict(schema='VIRALOS_SEMANTIC_FILM_REVIEW_V1',locale=locale,plan_sha256=PLAN[locale],source_video_sha256=pin,source_receipt_sha256=receipt_sha,master_receipt_sha256=master_sha,timeline_sha256=timeline_sha,frames=frames,shots=rows,source_raster=[960,540],states_per_shot=12,differing_bits=DIFFER,audio_payload_sha256=final,audio_payload_match=True,audit=audit,elapsed_seconds=round(time.monotonic()-start,2),caption_basis='omitted_no_verified_alignment',acoustic_alignment_verified=False,publication_authorized=False,human_review_required=True)
    b.dump(out/'receipt.json',report);(out/'INCOMPLETE').unlink();return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('locale','plan','video','timeline','timeline-sha','receipt','receipt-sha','font','output'):p.add_argument('--'+n,required=True)
    p.add_argument('--master');p.add_argument('--master-sha');print(json.dumps(render(**vars(p.parse_args())),ensure_ascii=False,indent=2))
