"""Pinned bilingual caption burn-in and signal-level QC; never authorizes release."""
import argparse, array, hashlib, json, math, re, shutil, subprocess, sys, time
from pathlib import Path
try:
    from . import phase14_bilingual as b, phase14_localize as loc, phase14_reviewed_timing as t, phase14_owner_assembly as en, phase14_preflight as pre
except ImportError:
    import phase14_bilingual as b, phase14_localize as loc, phase14_reviewed_timing as t, phase14_owner_assembly as en, phase14_preflight as pre


def pinned_json(path, pin, cap=2_000_000):
    raw=loc.read(path,cap)
    if loc.digest(raw)!=b.pin(pin):raise ValueError('receipt pin mismatch')
    obj=json.loads(raw)
    if not isinstance(obj,dict):raise ValueError('receipt object required')
    return obj


def check_chain(receipt,locale,source_pin,frames,fixture):
    schema,field={'en-US':('VIRALOS_OWNER_ASSEMBLY_REVIEW_V1','retime_sha256'),'hi-IN':('VIRALOS_HINDI_OWNER_REVIEW_V1','manifest_sha256')}[locale]
    if receipt.get('schema')!=schema or receipt.get('locale')!=locale or receipt.get(field)!=b.pin(source_pin) or type(receipt.get('frames')) is not int or receipt['frames']!=frames or receipt.get('artificial_pcm_fixture') is not fixture or receipt.get('caption_basis')!='omitted_no_verified_alignment' or receipt.get('acoustic_alignment_verified') is not False or receipt.get('publication_authorized') is not False or receipt.get('human_review_required') is not True or receipt.get('decode_pass') is not True:
        raise ValueError('source review chain mismatch')
    return b.pin(receipt['video_sha256'])


def ff(*args,timeout=300,cwd=None):
    return subprocess.run(['ffmpeg','-nostdin','-xerror',*args],check=True,capture_output=True,timeout=timeout,cwd=cwd)


def audio_hash(path):
    r=ff('-v','error','-i',str(path),'-map','0:a:0','-c','copy','-f','hash','-hash','sha256','-')
    s=r.stdout.decode('ascii').strip()
    if not re.fullmatch(r'SHA256=[0-9a-f]{64}',s):raise ValueError('invalid audio payload digest')
    return s[7:]


def signal_metrics(raw,rate=48000):
    if not raw or len(raw)%2 or len(raw)>rate*2*901:raise ValueError('invalid bounded mono PCM')
    samples=array.array('h');samples.frombytes(raw)
    if sys.byteorder!='little':samples.byteswap()
    peak=max(abs(x) for x in samples);clipped=sum(abs(x)>=32760 for x in samples)
    # Nonoverlapping 100ms windows; low RMS for >=2 seconds is a review flag.
    window=rate//10;streak=0;longest=0;intervals=[];start=0
    for i in range(0,len(samples),window):
        s=samples[i:i+window]
        quiet=sum(x*x for x in s)/len(s)<(32768*10**(-45/20))**2
        if quiet:
            if not streak:start=i
            streak+=len(s);longest=max(longest,streak)
        else:
            if streak>=2*rate:intervals.append([round(start/rate,3),round(i/rate,3)])
            streak=0
    if streak>=2*rate:intervals.append([round(start/rate,3),round(len(samples)/rate,3)])
    return dict(samples=len(samples),sample_peak_dbfs=round(20*math.log10(peak/32768),3) if peak else None,near_full_scale_samples=clipped,longest_quiet_seconds=round(longest/rate,3),quiet_intervals=intervals,quiet_threshold_dbfs=-45,quiet_min_seconds=2)


def visual_events(log):
    black=[];freeze=[]
    for line in log.splitlines():
        if 'black_start:' in line:
            m=re.search(r'black_start:([0-9.]+)\s+black_end:([0-9.]+)\s+black_duration:([0-9.]+)',line)
            if m:black.append([float(x) for x in m.groups()])
        if 'freeze_start:' in line or 'freeze_end:' in line:
            m=re.search(r'freeze_(start|end):\s*([0-9.]+)',line)
            if m:freeze.append(dict(event=m[1],seconds=float(m[2])))
    return dict(black_intervals=black,freeze_events=freeze,freeze_interpretation='review observation; static educational graphics may be intentional')


def scan(video,expected,frames):
    video=Path(video).resolve(strict=True)
    if video.stat().st_size>128*1024*1024 or b.q.sha(video)!=b.pin(expected):raise ValueError('video pin/size mismatch')
    if type(frames) is not int or not 720<=frames<=27000:raise ValueError('frame bounds')
    audit=b.audit(video,frames)
    if audit['video_sha256']!=expected:raise ValueError('video changed')
    pcm=ff('-v','error','-i',str(video),'-map','0:a:0','-ac','1','-ar','48000','-f','s16le','-').stdout
    audio=signal_metrics(pcm)
    r=ff('-hide_banner','-v','info','-i',str(video),'-an','-vf','scale=320:180,blackdetect=d=0.25:pix_th=0.10:pic_th=0.98,freezedetect=n=-50dB:d=2','-f','null','-')
    visual=visual_events(r.stderr.decode('utf8','replace'))
    if b.q.sha(video)!=expected:raise ValueError('video changed during scan')
    flags=[]
    if not audit['numeric_audio_gate_pass']:flags.append('NUMERIC_AUDIO_GATE_FAILED')
    if audio['near_full_scale_samples']:flags.append('NEAR_FULL_SCALE_SAMPLES')
    if audio['quiet_intervals']:flags.append('LONG_QUIET_INTERVAL')
    if visual['black_intervals']:flags.append('BLACK_INTERVAL')
    if visual['freeze_events']:flags.append('STATIC_OR_FREEZE_REVIEW')
    return dict(schema='VIRALOS_SIGNAL_QC_V1',audit=audit,audio=audio,visual=visual,review_flags=flags,semantic_quality_verified=False,publication_authorized=False,human_review_required=True)


def render(locale,plan,source,expected,timing,timing_sha,video,receipt,receipt_sha,output,fontpath,assets=None,fixture=False):
    start=time.monotonic();video=Path(video).resolve(strict=True);r=pinned_json(receipt,receipt_sha)
    if locale=='en-US':_,source_receipt,_,_=en.validate(plan,source,expected);frames=source_receipt['frames']
    elif locale=='hi-IN':_,rows,_,_=t.hindi_inputs(plan,source,assets,expected);frames=rows[-1]['end_frame']
    else:raise ValueError('unsupported locale')
    video_pin=check_chain(r,locale,expected,frames,fixture)
    if video.stat().st_size>128*1024*1024 or b.q.sha(video)!=video_pin:raise ValueError('source video hash/size mismatch')
    source_audit=b.audit(video,frames)
    if source_audit['video_sha256']!=video_pin:raise ValueError('source video changed')
    out=Path(output).resolve();out.mkdir(exist_ok=False);(out/'INCOMPLETE').touch()
    cap=t.compile_file(locale,plan,source,expected,timing,timing_sha,out/'captions',fontpath,assets,fixture)
    if cap['frames']!=frames:raise ValueError('caption duration mismatch')
    # Regenerate locally, never accept an arbitrary ASS filter program from the caller.
    ass=loc.read(out/'captions'/'review.ass',2_000_000)
    if loc.digest(ass)!=cap['ass_sha256']:raise ValueError('caption hash mismatch')
    (out/'fonts').mkdir();font=Path(fontpath)
    (out/'fonts'/'caption.ttf').write_bytes(loc.read(font,20_000_000))
    # Whole source including its existing warning/progress lane is scaled into top 900px.
    # Separate timing warning at y=925 and captions below it.
    dest=out/'captioned_review.mp4'
    ff('-v','error','-n','-i',str(video),'-map','0:v:0','-map','0:a:0','-vf','scale=1600:900:flags=lanczos,pad=1920:1080:160:0:color=0x101f32,ass=captions/review.ass:fontsdir=fonts','-c:v','libx264','-threads','4','-filter_threads','1','-preset','ultrafast','-crf','22','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(dest),cwd=out)
    source_audio=audio_hash(video);final_audio=audio_hash(dest)
    if source_audio!=final_audio or b.q.sha(video)!=video_pin:raise ValueError('audio payload or source changed')
    final_pin=b.q.sha(dest);qc=scan(dest,final_pin,frames)
    report=dict(schema='VIRALOS_INTEGRATED_OWNER_CAPTION_REVIEW_V1',locale=locale,source_sha256=expected,source_video_sha256=video_pin,source_receipt_sha256=receipt_sha,caption_receipt_sha256=b.q.sha(out/'captions'/'receipt.json'),timing_sha256=timing_sha,video_sha256=final_pin,frames=frames,words=cap['words'],audio_payload_sha256=final_audio,artificial_fixture=fixture,qc=qc,elapsed_seconds=round(time.monotonic()-start,2),acoustic_alignment_verified=False,publication_authorized=False,human_review_required=True)
    b.dump(out/'receipt.json',report);(out/'INCOMPLETE').unlink();return report


def readiness(qc,preflight):
    if qc.get('schema')!='VIRALOS_SIGNAL_QC_V1' or qc.get('publication_authorized') is not False or preflight.get('schema')!='VIRALOS_PHASE14_PREFLIGHT_V1' or preflight.get('publication_authorized') is not False:raise ValueError('invalid evidence schema')
    return dict(schema='VIRALOS_ACCEPTANCE_STATUS_V1',technical_decode_reported=qc['audit']['decode_pass'] is True,numeric_audio_reported=qc['audit']['numeric_audio_gate_pass'] is True,review_dependencies_reported=preflight['review_dependencies_detected'] is True,review_flags=qc['review_flags'],required_unverified=['licensed_natural_voice','independent_acoustic_alignment','native_editorial_rights_review','physical_windows_browser_restore','owner_authorized_private_upload'],production_accepted=False,publication_authorized=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('render')
    for n in ('locale','plan','source','expected','timing','timing-sha','video','receipt','receipt-sha','output','fontpath'):a.add_argument('--'+n,required=True)
    a.add_argument('--assets');a.add_argument('--fixture',action='store_true')
    a=sub.add_parser('scan');a.add_argument('--video',required=True);a.add_argument('--expected',required=True);a.add_argument('--frames',type=int,required=True);a.add_argument('--output',required=True)
    a=sub.add_parser('readiness')
    for n in ('qc','qc-sha','preflight','preflight-sha','output'):a.add_argument('--'+n,required=True)
    args=vars(p.parse_args());mode=args.pop('mode')
    if mode=='render':r=render(**args)
    else:
        output=args.pop('output')
        if mode=='scan':r=scan(**args)
        else:r=readiness(pinned_json(args['qc'],args['qc_sha']),pinned_json(args['preflight'],args['preflight_sha']))
        with Path(output).open('x',encoding='utf8') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps(r,indent=2))
if __name__=='__main__':main()
