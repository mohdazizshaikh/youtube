"""Read-only local environment preflight. Never installs, downloads or certifies acceptance."""
import argparse, importlib.metadata, json, platform, shutil, subprocess, sys
from pathlib import Path
from PIL import features, ImageFont

def check(fontpath=None, latinfont=None):
    result={'schema':'VIRALOS_PHASE14_PREFLIGHT_V1','platform':platform.system(),'python':platform.python_version(),'tools':{},'packages':{},'fonts':{},'checks':{},'owner_hardware_verified':False,'publication_authorized':False}
    for name in ('ffmpeg','ffprobe','piper','espeak'):
        path=shutil.which(name);result['tools'][name]={'present':bool(path)}
        if path and name in ('ffmpeg','ffprobe'):
            try:
                r=subprocess.run([path,'-version'],capture_output=True,text=True,timeout=10,check=True);result['tools'][name]['version']=r.stdout.splitlines()[0][:200]
            except (OSError,subprocess.SubprocessError,IndexError):result['tools'][name]['probe_failed']=True
    for pkg in ('Pillow','fastapi','uvicorn','httpx','pytest'):
        try:result['packages'][pkg]=importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:result['packages'][pkg]=None
    result['checks']['raqm']=features.check_feature('raqm')
    for key,path,text in [('mixed',fontpath,'एक अक्षर SHA-256'),('latin',latinfont,'SHA-256')]:
        try:
            p=Path(path) if path else None
            if not p or p.is_symlink() or not p.is_file():raise ValueError('missing regular font')
            font=ImageFont.truetype(str(p),55,layout_engine=ImageFont.Layout.RAQM);result['fonts'][key]={'loaded':font.getlength(text)>0,'family':font.getname()[0]}
        except (OSError,ValueError):result['fonts'][key]={'loaded':False}
    try:
        path=shutil.which('ffmpeg')
        if not path:raise ValueError('missing ffmpeg')
        r=subprocess.run([path,'-hide_banner','-encoders'],capture_output=True,text=True,timeout=10,check=True);names={line.split()[1] for line in r.stdout.splitlines() if len(line.split())>=2};result['checks']['h264_aac_encoders']={'libx264','aac'}<=names
        r=subprocess.run([path,'-hide_banner','-filters'],capture_output=True,text=True,timeout=10,check=True);names={line.split()[1] for line in r.stdout.splitlines() if len(line.split())>=2};result['checks']['ass_filter']='ass' in names
    except (ValueError,OSError,subprocess.SubprocessError):result['checks'].update(h264_aac_encoders=False,ass_filter=False)
    result['review_dependencies_detected']=all(result['checks'].values()) and all(v['loaded'] for v in result['fonts'].values()) and all(result['packages'].values()) and all(result['tools'][n].get('version') for n in ('ffmpeg','ffprobe'))
    result['natural_voice_runtime_verified']=False;result['acoustic_alignment_verified']=False;result['browser_verified']=False;result['font_glyph_coverage_verified']=False
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fontpath');p.add_argument('--latinfont');p.add_argument('--output',required=True);a=p.parse_args();r=check(a.fontpath,a.latinfont)
    with Path(a.output).open('x',encoding='utf8') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps(r,indent=2))
