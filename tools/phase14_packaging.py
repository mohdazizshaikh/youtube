"""Generate private, evidence-bound bilingual packaging concepts, never upload."""
import argparse, hashlib, json
from pathlib import Path
from PIL import Image, ImageDraw
try:
    from . import phase14_localize as l
except ImportError:
    import phase14_localize as l

def bits():
    a,b=(hashlib.sha256(s).digest() for s in (b'hello',b'Hello'))
    return [((x^y)>>i)&1 for x,y in zip(a,b) for i in range(7,-1,-1)]

def thumbnail(locale,fontpath,latinfont):
    if locale not in ('en-US','hi-IN'): raise ValueError('unsupported locale')
    im=Image.new('RGB',(1280,720),'#0c1b2d');d=ImageDraw.Draw(im); f=lambda n:l.font(fontpath,n); lf=lambda n:l.font(latinfont,n)
    d.rectangle((0,0,1280,13),fill='#55dfc9');l.line(d,'SHA-256',(62,53),lf(62),'#8ce7da',680)
    lines=('ONE LETTER.','125 BITS.') if locale=='en-US' else ('एक अक्षर।','125 बिट बदले।')
    for i,t in enumerate(lines):l.line(d,t,(62,173+i*103),f(79),'#ffffff' if i==0 else '#ffcf6c',685)
    l.line(d,'hello  →  Hello',(62,419),lf(53),'#d0e3f1',690)
    l.line(d,'Actual example: 125 / 256',(62,502),lf(31),'#c0d8e3',690)
    for i,v in enumerate(bits()):
        x=771+(i%16)*27;y=120+(i//16)*27;d.rounded_rectangle((x,y,x+21,y+21),3,fill='#ffbf59' if v else '#42a99e')
    d.rectangle((0,655,1280,720),fill='#162a3b');l.line(d,'DRAFT CONCEPT  •  REVIEW ONLY',(62,674),lf(25),'#ffe3a2',1150)
    return im

def build(hi_plan,video,receipt,timeline,output,fontpath,latinfont):
    p,hpin=l.load_plan(hi_plan); video=Path(video); rec=json.loads(l.read(receipt,100000)); t=json.loads(l.read(timeline,100000))
    vpin=l.digest(l.read(video,128*1024*1024))
    if rec.get('status')!='SYNTHETIC_PRIVATE_REVIEW_CANDIDATE' or rec.get('publication_authorized') is not False or rec.get('audit',{}).get('video_sha256')!=vpin or rec.get('timeline_sha256')!=l.digest(l.read(timeline,100000)) or t.get('plan_sha256')!=l.PIN: raise ValueError('review identity mismatch')
    shots=t.get('shots'); cursor=0
    if not isinstance(shots,list) or len(shots)!=24: raise ValueError('24 shots required')
    chapters=[]; names=['The one-character mystery','Bytes in, fingerprint out','Run the experiment','How much changed?','Check a downloaded file','Hashing is not encryption','Integrity is not authenticity','Your three-step takeaway']
    for i,r in enumerate(shots):
        if r['start_frame']!=cursor or type(r['end_frame']) is not int or r['end_frame']<=cursor or r['chapter']!=f'{i//3+1:02}' or r['beat']!=i%3: raise ValueError('invalid chapter order')
        if i%3==0: chapters.append(dict(start_seconds=cursor//30,title=names[i//3]))
        cursor=r['end_frame']
    if any(b['start_seconds']-a['start_seconds']<10 for a,b in zip(chapters,chapters[1:])) or cursor/30-chapters[-1]['start_seconds']<10: raise ValueError('short chapter')
    output=Path(output);output.mkdir(exist_ok=False);(output/'INCOMPLETE').touch()
    for loc,name in [('en-US','thumbnail_en.png'),('hi-IN','thumbnail_hi.png')]:thumbnail(loc,fontpath,latinfont).save(output/name)
    metadata=dict(schema='VIRALOS_PACKAGING_DRAFT_V1',english_video_sha256=vpin,hindi_plan_sha256=hpin,english={'title':'One Letter Changed 125 Bits: SHA-256 Explained','description':'Compare the exact bytes hello and Hello, count differing SHA-256 bits, and learn what a trusted checksum can and cannot prove. Synthetic review draft; not approved for upload.','chapters':chapters},hindi={'title':'एक अक्षर से 125 बिट बदले: SHA-256 समझिए','description':'hello और Hello की बाइटों का हैश निकालकर समझें कि इस प्रयोग में 256 में से 125 बिट क्यों अलग दिखते हैं और विश्वसनीय चेकसम की सीमा क्या है। समीक्षा हेतु मसौदा।','chapters':None,'video_sha256':None},experiment={'inputs':['hello','Hello'],'changed_bits':sum(bits()),'total_bits':256},thumbnail_sha256={n:l.digest(l.read(output/n,2_000_000)) for n in ('thumbnail_en.png','thumbnail_hi.png')},human_review_required=True,publication_authorized=False)
    (output/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf8');(output/'INCOMPLETE').unlink();return metadata
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('hi_plan','video','receipt','timeline','output','fontpath','latinfont'):p.add_argument('--'+n.replace('_','-'),type=Path,required=True)
    print(json.dumps(build(**vars(p.parse_args())),ensure_ascii=False,indent=2))
