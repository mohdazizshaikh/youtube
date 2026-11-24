"""Offline SHA-256 motion-graphics demo; never a release artifact."""
import argparse, hashlib, json, math, re, subprocess, time, wave
from pathlib import Path

SCENES = [
 ('One character changes the fingerprint', 'What happens when you change just one character in a file? A hash gives you a compact fingerprint of the bytes.', 'फ़ाइल का सिर्फ़ एक अक्षर बदलने पर क्या होता है? हैश बाइट्स का छोटा डिजिटल फ़िंगरप्रिंट देता है।'),
 ('Same algorithm. Different input.', 'Watch this experiment. We hash hello, then Hello with a capital H, using exactly the same algorithm.', 'इस प्रयोग में छोटे अक्षर वाले hello और बड़े H वाले Hello पर एक ही एल्गोरिदम चलाते हैं।'),
 ('Compare the 256 bits', 'Both outputs contain two hundred fifty six bits. The amber cells show which bits changed in this particular experiment.', 'दोनों आउटपुट में 256 बिट हैं। नारंगी खाने दिखाते हैं कि इस प्रयोग में कौन से बिट बदले।'),
 ('Integrity is not identity', 'Compare a downloaded file to a trusted reference hash. A match alone cannot prove who created the file. Trust the reference too.', 'डाउनलोड की गई फ़ाइल का हैश विश्वसनीय संदर्भ से मिलाएँ। समान हैश अकेले यह साबित नहीं करता कि फ़ाइल किसने बनाई।')]
A, B = [hashlib.sha256(x).hexdigest() for x in (b'hello', b'Hello')]
BITS = [bool((int(A,16)^int(B,16)) >> (255-i) & 1) for i in range(256)]
FPS=24

def run(*args):
 return subprocess.run(args,check=True,capture_output=True,text=True,timeout=180)

def stamp(n):
 m=round(n*1000/FPS); return f'{m//3600000:02}:{m//60000%60:02}:{m//1000%60:02}.{m%1000:03}'

def render(out,font,espeak='espeak'):
 from PIL import Image, ImageDraw, ImageFont
 t=time.monotonic(); out=Path(out); out.mkdir(exist_ok=False); (out/'INCOMPLETE').touch()
 fs={n:ImageFont.truetype(str(font),n) for n in (15,19,25,32,48)}; clips=[]; cues=['WEBVTT','']; cursor=0
 for i,(title,en,hi) in enumerate(SCENES):
  wav=out/f'{i}.wav'; pcm=out/f'{i}.pcm'; clip=out/f'{i}.mkv'
  run(espeak,'-v','en-us','-s','155','-w',str(wav),en)
  run('ffmpeg','-v','error','-i',str(wav),'-ac','1','-ar','48000','-f','s16le',str(pcm))
  data=pcm.read_bytes(); frames=math.ceil(len(data)/4000)+8
  with wave.open(str(wav),'wb') as w:
   w.setparams((1,2,48000,0,'NONE','not compressed')); w.writeframes(data+b'\0'*(frames*4000-len(data)))
  pcm.unlink()
  proc=subprocess.Popen(['ffmpeg','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','800x450','-r','24','-i','-','-i',str(wav),'-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p','-c:a','pcm_s16le',str(clip)],stdin=subprocess.PIPE)
  try:
   for j in range(frames):
    p=j/max(1,frames-1); im=Image.new('RGB',(800,450),'#0b192a'); d=ImageDraw.Draw(im)
    def txt(x,y,s,n=19,c='#eef6ff'): d.text((x,y),s,font=fs[n],fill=c)
    cyan='#69e4d5'; amber='#ffc16d'; muted='#9fb3c9'
    d.rectangle((0,0,800,5),fill=cyan); txt(32,24,f'0{i+1}  /  SHA-256 LAB',15,cyan); txt(32,54,title,32); d.line((32,109,768,109),fill='#30485e',width=2)
    if i<2:
     for k,(word,digest) in enumerate((('hello',A),('Hello',B))):
      y=135+k*105; x=32+int(28*max(0,1-j/24)); d.rounded_rectangle((x,y,768,y+86),12,fill='#173047'); txt(x+16,y+23,word,32,cyan if k==0 else amber); n=int(64*min(1,p*2)); txt(x+170,y+15,digest[:min(32,n)],19); txt(x+170,y+45,digest[32:n],19)
    elif i==2:
     n=int(256*min(1,p*2))
     for k,b in enumerate(BITS):
      x=32+k%32*15; y=139+k//32*22; d.rounded_rectangle((x,y,x+11,y+16),2,fill=(amber if b else cyan) if k<n else '#294259')
     txt(550,162,str(sum(BITS[:n])),48,amber); txt(550,225,'bits changed',19,muted); txt(32,334,'Amber = changed   |   Teal = unchanged',19,muted)
    else:
     for k,(label,value,color) in enumerate((('TRUSTED REFERENCE','Compare the full hash',cyan),('AUTHOR / ORIGIN','Needs separate evidence',amber))):
      y=135+k*105; x=32+int(28*max(0,1-j/24)); d.rounded_rectangle((x,y,768,y+86),12,fill='#173047'); txt(x+16,y+12,label,15,color); txt(x+16,y+38,value,25)
    txt(32,398,'VIRALOS / TECHNICAL PREVIEW',15,muted); txt(590,398,'Synthetic narration',15,muted); d.rectangle((32,430,768,434),fill='#294259'); d.rectangle((32,430,32+int(736*p),434),fill=cyan); proc.stdin.write(im.tobytes())
  finally:
   proc.stdin.close()
   if proc.wait(timeout=180): raise RuntimeError('encode failed')
  clips.append(clip); cues.extend([f'{stamp(cursor)} --> {stamp(cursor+frames)}',en,'']); cursor+=frames; wav.unlink()
 (out/'captions.vtt').write_text('\n'.join(cues),encoding='utf-8'); (out/'concat.txt').write_text('\n'.join(f"file '{p.name}'" for p in clips),encoding='utf-8')
 final=out/'preview.mp4'; inputs=('-f','concat','-safe','1','-i',str(out/'concat.txt'))
 target='loudnorm=I=-16:TP=-2:LRA=7'
 scan=run('ffmpeg','-hide_banner',*inputs,'-af',target+':print_format=json','-f','null','-').stderr
 pre=json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}',scan,re.S).group())
 filt=target+':measured_I='+pre['input_i']+':measured_TP='+pre['input_tp']+':measured_LRA='+pre['input_lra']+':measured_thresh='+pre['input_thresh']+':offset='+pre['target_offset']+':linear=true'
 run('ffmpeg','-v','error',*inputs,'-c:v','copy','-af',filt,'-ar','48000','-c:a','aac','-b:a','160k','-movflags','+faststart',str(final))
 stats=json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}',run('ffmpeg','-hide_banner','-i',str(final),'-af','loudnorm=print_format=json','-f','null','-').stderr,re.S).group()); probe=json.loads(run('ffprobe','-v','error','-show_format','-show_streams','-of','json',str(final)).stdout)
 report={'status':'SYNTHETIC_PREVIEW_ONLY','publication_authorized':False,'duration_s':float(probe['format']['duration']),'elapsed_s':round(time.monotonic()-t,2),'integrated_lufs':float(stats['input_i']),'true_peak_dbtp':float(stats['input_tp']),'audio_target_pass':abs(float(stats['input_i'])+16)<=1 and float(stats['input_tp'])<=-1,'audio_target_lufs':-16,'audio_peak_ceiling_dbtp':-1,'caption_basis':'scene, not word aligned','video_sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'experiment':{'hello':A,'Hello':B,'changed_bits':sum(BITS)},'sources':['https://www.nist.gov/publications/secure-hash-standard','https://docs.python.org/3/library/hashlib.html'],'scripts':[{'en':s[1],'hi':s[2]} for s in SCENES]}
 (out/'receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 for p in [*clips,out/'concat.txt']: p.unlink()
 (out/'INCOMPLETE').unlink(); return report

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path,required=True); p.add_argument('--font',type=Path,required=True); p.add_argument('--espeak',default='espeak'); a=p.parse_args(); print(json.dumps(render(a.output,a.font,a.espeak),ensure_ascii=False,indent=2))
