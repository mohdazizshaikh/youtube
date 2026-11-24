"""Construct explicitly artificial word timings from the Phase 14E synthetic WAV; never use for release."""
import argparse
import json
import wave
from pathlib import Path
try:
    from . import phase14_caption_timeline as caps
except ImportError:
    import phase14_caption_timeline as caps


def make(plan_path, timeline_path, narration, output):
    if caps.quality.sha(plan_path) != caps.assembly.PLAN_SHA:
        raise ValueError('pinned English plan required')
    reference = caps.assembly.segments(caps.load(plan_path))
    timeline = caps.load(timeline_path)['shots']
    frames = caps.assembly.check_timeline(timeline)
    output = Path(output)
    output.mkdir(exist_ok=False)
    (output/'INCOMPLETE').touch()
    assets = output/'assets'
    assets.mkdir()
    manifest = dict(schema=1, locale='en-US', basis='synthetic_fixture', plan_sha256=caps.quality.sha(plan_path), timeline_sha256=caps.quality.sha(timeline_path), narration_sha256=caps.quality.sha(narration), shots=[])
    with wave.open(str(narration), 'rb') as full:
        caps.pcm_header(full, frames * caps.SAMPLES)
        for i, (r, ref) in enumerate(zip(timeline, reference)):
            s, w, j = [assets/f'{i:02}.{e}' for e in ('txt','wav','json')]
            s.write_text(ref['text'], encoding='utf-8')
            data = full.readframes(r['samples'])
            if len(data) != 2*r['samples'] or full.readframes(r['padding_samples']) != b'\0'*(2*r['padding_samples']):
                raise ValueError('PCM or padding mismatch')
            with wave.open(str(w),'wb') as f:
                f.setparams((1,2,caps.RATE,0,'NONE','not compressed'))
                f.writeframes(data)
            tokens = ref['text'].split()
            duration = r['samples']*1000//caps.RATE
            if duration//len(tokens) < 40:
                raise ValueError('fixture word duration too short')
            words = [dict(text=t,start_ms=k*duration//len(tokens),end_ms=(k+1)*duration//len(tokens)) for k,t in enumerate(tokens)]
            j.write_text(json.dumps(dict(locale='en-US',basis='synthetic_fixture',script_sha256=caps.quality.sha(s),wav_sha256=caps.quality.sha(w),words=words),indent=2)+'\n',encoding='utf-8')
            manifest['shots'].append(dict(index=i,txt_sha256=caps.quality.sha(s),wav_sha256=caps.quality.sha(w),json_sha256=caps.quality.sha(j)))
    dest=output/'manifest.json'
    dest.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (output/'INCOMPLETE').unlink()
    return dest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','timeline','narration','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    print(make(a.plan,a.timeline,a.narration,a.output))
