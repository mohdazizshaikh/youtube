"""Explicit opt-in local Piper CLI adapter. No downloads, license certification or release."""
import argparse, json, subprocess, wave, io
from pathlib import Path
try:
    from . import phase14_localize as loc, phase14_bilingual as b, phase14_quality as q
except ImportError:
    import phase14_localize as loc, phase14_bilingual as b, phase14_quality as q


def inspect(manifest, expected):
    raw=loc.read(manifest,50000);m=json.loads(raw)
    if loc.digest(raw)!=b.pin(expected) or m.get('schema')!='VIRALOS_LOCAL_PIPER_V1' or m.get('locale') not in ('en-US','en-IN','hi-IN') or m.get('rights_attested') is not True or not isinstance(m.get('rights_reference'),str) or not m['rights_reference'].strip():raise ValueError('pinned local runtime and private rights declaration required')
    paths={}
    for name,cap in [('executable',200_000_000),('model',1_000_000_000),('config',2000000)]:
        obj=m.get(name)
        if not isinstance(obj,dict) or set(obj)!={'path','sha256'} or not isinstance(obj['path'],str):raise ValueError('exact asset entry required')
        p=Path(obj['path']);pin=b.pin(obj['sha256'])
        if not p.is_absolute() or p.is_symlink() or not p.is_file() or not 0<p.stat().st_size<=cap or q.sha(p)!=pin:raise ValueError('local runtime asset hash/size mismatch')
        paths[name]=p
    config=json.loads(loc.read(paths['config'],2000000));rate=config.get('audio',{}).get('sample_rate')
    if type(rate) is not int or not 8000<=rate<=48000:raise ValueError('invalid config sample rate')
    return m,paths,rate


def synthesize(manifest,expected,script,script_sha,output):
    m,paths,rate=inspect(manifest,expected);text=loc.read(script,12000)
    if loc.digest(text)!=b.pin(script_sha) or not text.decode('utf8').strip():raise ValueError('script hash/empty mismatch')
    out=Path(output).resolve();out.mkdir(exist_ok=False);(out/'INCOMPLETE').touch();raw=out/'raw.wav';dest=out/'voice.wav'
    # Run only an explicitly selected, trusted owner executable; never fetch a model.
    subprocess.run([str(paths['executable']),'--model',str(paths['model']),'--config',str(paths['config']),'--output_file',str(raw)],input=text+b'\n',check=True,timeout=120,capture_output=True,cwd=out)
    data=loc.read(raw,20_000_000)
    with wave.open(io.BytesIO(data),'rb') as w:
        if w.getnchannels()!=1 or w.getsampwidth()!=2 or w.getframerate()!=rate or w.getcomptype()!='NONE' or not rate<=w.getnframes()<=90*rate or len(w.readframes(w.getnframes()))!=2*w.getnframes():raise ValueError('unexpected Piper WAV')
    loc.run('ffmpeg','-v','error','-xerror','-nostdin','-n','-i',str(raw),'-ac','1','-ar','48000','-c:a','pcm_s16le',str(dest),timeout=120)
    _,n=loc.pcm(loc.read(dest,9000000));inspect(manifest,expected)
    report=dict(schema='VIRALOS_LOCAL_PIPER_OUTPUT_V1',locale=m['locale'],runtime_manifest_sha256=expected,script_sha256=script_sha,wav_sha256=q.sha(dest),samples=n,natural_voice_verified=False,listening_attested=False,acoustic_alignment_verified=False,publication_authorized=False,human_review_required=True)
    b.dump(out/'receipt.json',report);(out/'INCOMPLETE').unlink();return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True)
    for cmd,fields in [('inspect','manifest expected'),('synthesize','manifest expected script script_sha output')]:
        a=s.add_parser(cmd)
        for n in fields.split():a.add_argument('--'+n.replace('_','-'),required=True)
    x=vars(p.parse_args());cmd=x.pop('cmd')
    if cmd=='inspect':
        m,_,rate=inspect(**x);print(json.dumps(dict(locale=m['locale'],sample_rate=rate,asset_hashes_verified=True,inference_tested=False,publication_authorized=False)))
    else:print(json.dumps(synthesize(**x),indent=2))
