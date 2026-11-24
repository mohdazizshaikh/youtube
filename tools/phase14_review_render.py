"""Synthetic captioned private-review render; never release authority."""
import argparse
import json
import re
import subprocess
import time
from pathlib import Path
try:
    from . import phase14_assembly as assembly, phase14_caption_timeline as captions, phase14_quality as quality
except ImportError:
    import phase14_assembly as assembly, phase14_caption_timeline as captions, phase14_quality as quality


def run(*args, cwd=None, timeout=300):
    return subprocess.run(args, cwd=cwd, timeout=timeout, check=True, capture_output=True, text=True)


def validate_chain(raw, mastered, timeline, master_receipt):
    t, m = captions.load(timeline), captions.load(master_receipt)
    frames = assembly.check_timeline(t['shots'])
    if t.get('video_sha256') != quality.sha(raw) or t.get('plan_sha256') != assembly.PLAN_SHA or t.get('voice_basis') != 'synthetic eSpeak English' or t.get('publication_authorized') is not False:
        raise ValueError('invalid synthetic source receipt')
    if m.get('source_sha256') != t['video_sha256'] or m.get('output_sha256') != quality.sha(mastered) or m.get('numeric_gate_pass') is not True or m.get('publication_authorized') is not False:
        raise ValueError('invalid mastering chain')
    return t, m, frames


def audio_hash(video):
    s = run('ffmpeg','-v','error','-nostdin','-i',str(video),'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-').stdout.strip()
    if not re.fullmatch(r'SHA256=[0-9a-f]{64}',s):
        raise ValueError('unexpected audio packet hash')
    return s[7:]


def warning_ass(s, last, frames):
    old = f"Dialogue: 1,0:00:00.00,{captions.clock(round(last*100))},Warning,,0,0,0,,SYNTHETIC TIMING TEST - NOT ALIGNED"
    new = f"Dialogue: 1,0:00:00.00,{captions.clock((frames*100+29)//30)},Warning,,0,0,0,,SYNTHETIC TIMING TEST - NOT ALIGNED"
    if s.count(old)!=1:
        raise ValueError('missing synthetic timing warning')
    return s.replace(old,new)


def render(plan, raw, mastered, timeline, master_receipt, narration, manifest, assets, output):
    start = time.monotonic()
    plan, raw, mastered, timeline, master_receipt, narration, manifest, assets, output = map(lambda p: Path(p).resolve(), (plan,raw,mastered,timeline,master_receipt,narration,manifest,assets,output))
    t,m,frames = validate_chain(raw,mastered,timeline,master_receipt)
    if captions.load(manifest).get('basis') != 'synthetic_fixture':
        raise ValueError('synthetic review only; owner footage needs separate reviewed pipeline')
    output.mkdir(exist_ok=False)
    (output/'INCOMPLETE').touch()
    r = captions.compile_timeline(plan,timeline,narration,manifest,assets,output/'captions')
    if r['frames'] != frames or r['basis'] != 'synthetic_fixture' or r['publication_authorized'] is not False:
        raise ValueError('caption chain mismatch')
    s = (output/'captions/global_highlight.ass').read_text(encoding='utf-8')
    (output/'review.ass').write_text(warning_ass(s,r['last_caption_s'],frames),encoding='utf-8')
    dest = output/'captioned_review.mp4'
    ah = audio_hash(mastered)
    run('ffmpeg','-v','error','-xerror','-nostdin','-threads','4','-i',str(mastered),'-map','0:v:0','-map','0:a:0','-filter_threads','2','-vf','scale=1728:972:flags=lanczos,pad=1920:1080:96:0:color=0x0b1829,ass=review.ass','-c:v','libx264','-preset','ultrafast','-crf','23','-threads','4','-c:a','copy','-movflags','+faststart',str(dest),cwd=output,timeout=600)
    audit = assembly.audit(dest,quality.sha(dest),t['shots'],require_mastered=True)
    if audio_hash(dest)!=ah or quality.sha(mastered)!=m['output_sha256']:
        raise ValueError('audio changed or source mutated')
    receipt = dict(status='SYNTHETIC_PRIVATE_REVIEW_CANDIDATE',source_sha256=m['output_sha256'],raw_source_sha256=t['video_sha256'],timeline_sha256=quality.sha(timeline),caption_receipt_sha256=quality.sha(output/'captions/receipt.json'),review_ass_sha256=quality.sha(output/'review.ass'),audio_packet_sha256=ah,audio_packet_hash_match=True,words=r['words'],shots=r['shots'],caption_basis='synthetic_fixture',caption_strip_px=108,acoustic_alignment_verified=False,editorial_review_required=True,publication_authorized=False,queue_enqueued=False,elapsed_s=round(time.monotonic()-start,2),audit=audit)
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    (output/'INCOMPLETE').unlink()
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','raw','mastered','timeline','master_receipt','narration','manifest','assets','output'):
        p.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    print(json.dumps(render(**vars(p.parse_args())),indent=2))
