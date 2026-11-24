"""Offline, hash-bound segmented narration and global word captions; no release authority."""
import argparse
import json
import re
import unicodedata
import wave
from pathlib import Path
try:
    from . import phase14_assembly as assembly, phase14_quality as quality
except ImportError:
    import phase14_assembly as assembly, phase14_quality as quality

LOCALES = {'en-US', 'en-IN', 'hi-IN'}
BASES = {'synthetic_fixture', 'owner_reviewed_manual', 'owner_reviewed_ctc'}
RATE = assembly.RATE
SAMPLES = assembly.SAMPLES
MAX_LINE = 42


def load(path, limit=2_000_000):
    path = Path(path)
    if path.stat().st_size > limit:
        raise ValueError('JSON exceeds limit')
    return json.loads(path.read_text(encoding='utf-8'))


def safe_file(root, name):
    if not isinstance(name, str) or not re.fullmatch(r'[0-9]{2}\.(?:txt|wav|json)', name):
        raise ValueError('invalid asset name')
    p = root / name
    if p.is_symlink() or not p.is_file() or p.resolve().parent != root:
        raise ValueError('unsafe or missing asset')
    return p


def pcm_header(w, frames):
    if (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getcomptype(), w.getnframes()) != (1, 2, RATE, 'NONE', frames):
        raise ValueError('expected exact mono PCM16 48kHz sample count')


def safe_token(token):
    # Allow script-shaping joiners in Devanagari, but reject controls and ASS escapes.
    return (0 < len(token) <= MAX_LINE and not any(c in '{}\\<>' or (unicodedata.category(c).startswith('C') and c not in '\u200c\u200d') for c in token))


def validate_inputs(plan_path, timeline_path, narration_path, manifest_path, assets):
    assets = Path(assets).resolve()
    plan = load(plan_path)
    if quality.sha(plan_path) != assembly.PLAN_SHA:
        raise ValueError('pinned original English reference plan required')
    reference = assembly.segments(plan)
    timeline = load(timeline_path)['shots']
    frames = assembly.check_timeline(timeline)
    manifest = load(manifest_path)
    locale, basis = manifest.get('locale'), manifest.get('basis')
    if manifest.get('schema') != 1 or locale not in LOCALES or basis not in BASES:
        raise ValueError('unsupported locale or timing provenance')
    if manifest.get('plan_sha256') != quality.sha(plan_path) or manifest.get('timeline_sha256') != quality.sha(timeline_path) or manifest.get('narration_sha256') != quality.sha(narration_path):
        raise ValueError('plan, timeline or narration hash mismatch')
    if basis != 'synthetic_fixture' and (manifest.get('rights_attested') is not True or manifest.get('listening_attested') is not True or not isinstance(manifest.get('rights_reference'), str) or not manifest['rights_reference'].strip()):
        raise ValueError('private rights and listening declarations required')
    entries = manifest.get('shots')
    if not isinstance(entries, list) or len(entries) != len(timeline):
        raise ValueError('exact 24-shot inventory required')
    global_words = []
    with wave.open(str(narration_path), 'rb') as full:
        pcm_header(full, frames * SAMPLES)
        for i, (entry, rec, ref) in enumerate(zip(entries, timeline, reference)):
            if not isinstance(entry, dict) or type(entry.get('index')) is not int or entry['index'] != i:
                raise ValueError('shot order mismatch')
            files = {ext: safe_file(assets, f'{i:02}.{ext}') for ext in ('txt', 'wav', 'json')}
            if any(entry.get(f'{ext}_sha256') != quality.sha(path) for ext, path in files.items()):
                raise ValueError('shot asset hash mismatch')
            script = files['txt'].read_text(encoding='utf-8')
            if locale.startswith('en') and script.split() != ref['text'].split():
                raise ValueError('English shot differs from pinned script')
            if locale == 'hi-IN' and not any('\u0900' <= c <= '\u097f' for c in script):
                raise ValueError('Hindi draft must contain Devanagari')
            words_manifest = load(files['json'])
            if words_manifest.get('locale') != locale or words_manifest.get('basis') != basis:
                raise ValueError('shot provenance mismatch')
            words = quality.validate_words(files['txt'], files['wav'], words_manifest)
            if any(not safe_token(w['text']) for w in words):
                raise ValueError('unsupported caption token')
            with wave.open(str(files['wav']), 'rb') as shot:
                pcm_header(shot, rec['samples'])
                audio = shot.readframes(rec['samples'])
            if len(audio) != rec['samples'] * 2 or not any(audio):
                raise ValueError('truncated or silent shot')
            if full.readframes(rec['samples']) != audio or full.readframes(rec['padding_samples']) != b'\0' * (2 * rec['padding_samples']):
                raise ValueError('assembled PCM differs from shot bytes or zero padding')
            offset_samples = rec['start_frame'] * SAMPLES
            for w in words:
                # Integer sample arithmetic, flooring to ASS centiseconds, no crossing shot boundary.
                a = (offset_samples + w['start_ms'] * (RATE // 1000)) * 100 // RATE
                b = (offset_samples + w['end_ms'] * (RATE // 1000)) * 100 // RATE
                if b <= a or b > rec['end_frame'] * 100 // assembly.FPS or (global_words and a < global_words[-1]['end_cs']):
                    raise ValueError('global caption overlap or shot boundary violation')
                global_words.append(dict(shot=i, text=w['text'], start_cs=a, end_cs=b))
        if full.readframes(1):
            raise ValueError('unexpected trailing PCM')
    return manifest, global_words, frames


def groups(words):
    group = []
    for w in words:
        if group and (w['shot'] != group[-1]['shot'] or len(group) == 4 or len(' '.join(x['text'] for x in [*group, w])) > MAX_LINE or w['start_cs'] - group[-1]['end_cs'] > 40):
            yield group
            group = []
        group.append(w)
    if group:
        yield group


def clock(cs):
    return quality.ass_clock(cs * 10)


def compile_ass(words, locale, basis):
    font = 'Noto Sans Devanagari' if locale == 'hi-IN' else 'Noto Sans'
    header = f'''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},44,&H00FFFFFF,&H00FFFFFF,&H00101929,&H80101929,-1,0,0,0,100,100,0,0,3,8,0,2,120,120,42,1
Style: Warning,Noto Sans,26,&H0000D6FF,&H00FFFFFF,&H00101929,&H80101929,-1,0,0,0,100,100,0,0,3,5,0,8,120,120,18,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines = []
    for group in groups(words):
        for w in group:
            phrase = ' '.join((r'{\c&H00D6FF&}'+x['text']+r'{\c&HFFFFFF&}') if x is w else x['text'] for x in group)
            lines.append(f"Dialogue: 0,{clock(w['start_cs'])},{clock(w['end_cs'])},Default,,0,0,0,,{phrase}")
    if basis == 'synthetic_fixture':
        lines.insert(0, f"Dialogue: 1,0:00:00.00,{clock(words[-1]['end_cs'])},Warning,,0,0,0,,SYNTHETIC TIMING TEST - NOT ALIGNED")
    return header + '\n'.join(lines) + '\n'


def compile_timeline(plan, timeline, narration, manifest_path, assets, output):
    manifest, words, frames = validate_inputs(plan, timeline, narration, manifest_path, assets)
    output = Path(output)
    output.mkdir(exist_ok=False)
    (output/'INCOMPLETE').touch()
    ass = output/'global_highlight.ass'
    ass.write_text(compile_ass(words, manifest['locale'], manifest['basis']), encoding='utf-8')
    (output/'global_words.json').write_text(json.dumps(words, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    receipt = dict(status='CAPTION_TIMELINE_ONLY', locale=manifest['locale'], basis=manifest['basis'], shots=24, words=len(words), frames=frames, duration_s=frames/assembly.FPS, last_caption_s=words[-1]['end_cs']/100, narration_sha256=quality.sha(narration), timeline_sha256=quality.sha(timeline), manifest_sha256=quality.sha(manifest_path), ass_sha256=quality.sha(ass), global_words_sha256=quality.sha(output/'global_words.json'), pcm_assembly_match=True, acoustic_alignment_verified=False, rendered_video_audio_match_verified=False, publication_authorized=False, native_review_required=True)
    (output/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    (output/'INCOMPLETE').unlink()
    return receipt


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('plan','timeline','narration','manifest','assets','output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(compile_timeline(a.plan,a.timeline,a.narration,a.manifest,a.assets,a.output), indent=2))
