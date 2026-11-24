"""Private offline mastering and reviewed-word caption preparation; never release authority."""
import argparse
import hashlib
import json
import math
import re
import subprocess
import wave
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=300)


def measure(path):
    raw = run('ffmpeg', '-hide_banner', '-nostdin', '-i', str(path), '-map', '0:a:0', '-af', 'loudnorm=print_format=json', '-f', 'null', '-').stderr
    j = json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}', raw, re.S)[-1])
    values = {k: float(j[k]) for k in ('input_i', 'input_tp', 'input_lra')}
    if not all(math.isfinite(x) for x in values.values()):
        raise ValueError('nonfinite loudness; silence or invalid input')
    return values


def accepted(m):
    return abs(m['input_i'] + 16) <= 1 and m['input_tp'] <= -1


def master(source, output, expected_sha):
    source, output = Path(source).resolve(), Path(output).resolve()
    if sha(source) != expected_sha:
        raise ValueError('source hash mismatch')
    before = measure(source)
    output.mkdir(exist_ok=False)
    (output / 'INCOMPLETE').touch()
    # Bounded gain search; every candidate is encoded from the same original input.
    base = max(-12, min(12, -16 - before['input_i']))
    trials = []
    for i, adjustment in enumerate((0, .5, -.5, 1, -1)):
        gain = max(-12, min(12, base + adjustment))
        candidate = output / f'trial-{i}.mp4'
        filt = f'volume={gain:.4f}dB,aresample=192000,alimiter=limit=0.84:attack=5:release=50:level=0:latency=1,aresample=48000'
        run('ffmpeg', '-v', 'error', '-nostdin', '-n', '-i', str(source), '-map', '0:v:0', '-map', '0:a:0', '-map_metadata', '-1', '-map_chapters', '-1', '-c:v', 'copy', '-af', filt, '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(candidate))
        m = measure(candidate)
        trials.append({'file': candidate.name, 'gain_db': gain, **m, 'pass': accepted(m)})
        if accepted(m):
            break
    good = [x for x in trials if x['pass']]
    if not good:
        (output / 'failure.json').write_text(json.dumps(trials, indent=2), encoding='utf-8')
        raise ValueError('no candidate met numeric mastering gate')
    final = output / 'mastered.mp4'
    (output / good[0]['file']).rename(final)
    run('ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-i', str(final), '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-')
    if sha(source) != expected_sha:
        raise ValueError('source changed during processing')
    report = {'source_sha256': expected_sha, 'output_sha256': sha(final), 'before': before, 'after': measure(final), 'trials': trials, 'numeric_gate_pass': True, 'publication_authorized': False, 'human_listening_required': True}
    if not accepted(report['after']):
        raise ValueError('final measurement failed')
    (output / 'receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (output / 'INCOMPLETE').unlink()
    return report


def validate_words(script, wav, manifest):
    script, wav = Path(script), Path(wav)
    if manifest.get('locale') not in ('hi-IN', 'en-IN', 'en-US', 'en-GB'):
        raise ValueError('unsupported locale')
    if manifest.get('basis') not in ('owner_reviewed_manual', 'owner_reviewed_ctc', 'synthetic_fixture'):
        raise ValueError('timing provenance required')
    if manifest.get('wav_sha256') != sha(wav) or manifest.get('script_sha256') != sha(script):
        raise ValueError('input hash mismatch')
    with wave.open(str(wav), 'rb') as w:
        if w.getcomptype() != 'NONE' or w.getnchannels() not in (1, 2) or w.getsampwidth() != 2 or not 8000 <= w.getframerate() <= 48000:
            raise ValueError('expected bounded PCM16 WAV')
        duration = w.getnframes() * 1000 // w.getframerate()
        if not 0 < duration <= 600000:
            raise ValueError('invalid duration')
        if len(w.readframes(w.getnframes())) != w.getnframes() * w.getnchannels() * 2:
            raise ValueError('truncated PCM')
    tokens = script.read_text(encoding='utf-8').split()
    words = manifest.get('words')
    if not isinstance(words, list) or not tokens or len(tokens) != len(words) or len(words) > 5000:
        raise ValueError('word count mismatch')
    end = 0
    for token, word in zip(tokens, words):
        if not isinstance(word, dict) or word.get('text') != token or any(c in token for c in '{}\\<>') or any(ord(c) < 32 for c in token) or len(token) > 60:
            raise ValueError('token mismatch or unsupported caption character')
        a, b = word.get('start_ms'), word.get('end_ms')
        if type(a) is not int or type(b) is not int or not end <= a < b <= duration or b-a < 40:
            raise ValueError('overlap, duration or timestamp error')
        end = b
    return words


def ass_clock(ms):
    cs = ms // 10
    return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'


def captions(script, wav, manifest, output):
    words = validate_words(script, wav, manifest)
    output = Path(output)
    output.mkdir(exist_ok=False)
    (output / 'INCOMPLETE').touch()
    header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans,52,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,100,100,100,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines = []
    for i, word in enumerate(words):
        group = words[(i//4)*4:(i//4)*4+4]
        text = ' '.join((r'{\c&H00D6FF&}' + w['text'] + r'{\c&HFFFFFF&}') if w is word else w['text'] for w in group)
        lines.append(f"Dialogue: 0,{ass_clock(word['start_ms'])},{ass_clock(word['end_ms'])},Default,,0,0,0,,{text}")
    dest = output / 'highlight.ass'
    dest.write_text(header + '\n'.join(lines) + '\n', encoding='utf-8')
    report = {'locale': manifest['locale'], 'basis': manifest['basis'], 'word_count': len(words), 'wav_sha256': sha(wav), 'script_sha256': sha(script), 'ass_sha256': sha(dest), 'publication_authorized': False, 'timing_accuracy_verified': False, 'font_and_native_playback_review_required': True}
    (output / 'receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    (output / 'INCOMPLETE').unlink()
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    m = sub.add_parser('master'); m.add_argument('source'); m.add_argument('output'); m.add_argument('--sha256', required=True)
    c = sub.add_parser('captions'); c.add_argument('script'); c.add_argument('wav'); c.add_argument('manifest'); c.add_argument('output')
    a = p.parse_args()
    result = master(a.source, a.output, a.sha256) if a.command == 'master' else captions(a.script, a.wav, json.loads(Path(a.manifest).read_text(encoding='utf-8')), a.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
