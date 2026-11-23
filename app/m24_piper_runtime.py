"""Owner-operated **offline-capable** Piper CLI adapter for original narration drafts.

The owner must install Piper and supply the voice model, its matching config,
file hashes and licence review. No dependency is downloaded and no outbound API
is called by this module. An arbitrary third-party executable cannot be proven
network-free merely by passing environment variables; owners must trust/audit
that binary. The result is a *draft*, never a licensed, natural or publishable
voice without independent review.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .m24_audio import SUPPORTED_LOCALES, split_words, wav_audio_qa

_SHA = re.compile(r"^[0-9a-f]{64}$")
MAX_TEXT_CHARS = 650
MAX_SECONDS = 120
MAX_WAV_BYTES = 40 * 1024 * 1024


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _regular(path: Path, label: str, limit: int) -> Path:
    path = Path(path).expanduser()
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= limit:
        raise ValueError(f'{label} must be an existing bounded, non-symlink regular file')
    return path.resolve(strict=True)


def preflight_piper(profile: dict, locale: str, binary: Path) -> dict:
    """Fail closed on model/config/binary tampering and unverifiable rights."""
    if locale not in SUPPORTED_LOCALES or not isinstance(profile, dict):
        raise ValueError('Unsupported Piper voice locale/profile')
    if profile.get('backend') != 'piper' or profile.get('locale') != locale:
        raise ValueError('Piper backend and requested locale must match')
    if profile.get('rights_attested') is not True or not isinstance(profile.get('license_reference'), str) or not 12 <= len(profile['license_reference'].strip()) <= 500:
        raise ValueError('Specific owner-reviewed voice licence reference required')
    if profile.get('commercial_use_allowed_per_owner') is not True:
        raise ValueError('Owner must separately attest intended commercial use rights')
    if profile.get('cloned_voice') is True and profile.get('speaker_consent') is not True:
        raise ValueError('Cloned speaker voice requires recorded consent')
    paths = {
        'model': _regular(Path(str(profile.get('model_file', ''))), 'Voice model', 4 * 1024**3),
        'config': _regular(Path(str(profile.get('config_file', ''))), 'Piper config', 128 * 1024),
        'binary': _regular(Path(binary), 'Piper executable', 120 * 1024**2),
    }
    if len(set(paths.values())) != 3 or paths['model'].suffix != '.onnx' or paths['config'].suffix != '.json':
        raise ValueError('Distinct ONNX model, JSON config and Piper binary required')
    for label, field in [('model','sha256'),('config','config_sha256'),('binary','piper_binary_sha256')]:
        expected = profile.get(field)
        if not isinstance(expected, str) or not _SHA.fullmatch(expected) or sha256_file(paths[label]) != expected:
            raise ValueError(f'Piper {label} hash missing or changed')
    try:
        config = json.loads(paths['config'].read_text('utf-8'))
    except (ValueError, UnicodeError) as ex:
        raise ValueError('Invalid Piper voice config JSON') from ex
    if not isinstance(config, dict) or not isinstance(config.get('audio'), dict):
        raise ValueError('Piper config missing audio sample rate')
    rate = config['audio'].get('sample_rate')
    if type(rate) is not int or not 16000 <= rate <= 48000:
        raise ValueError('Unsupported Piper sample rate (16–48kHz)')
    lang = config.get('language')
    if not isinstance(lang, dict) or not isinstance(lang.get('code'), str):
        raise ValueError('Piper config must provide an auditable language code')
    code = lang['code'].replace('_', '-').lower()
    if code != locale.lower():
        raise ValueError('Voice model language code differs from target locale')
    if os.name != 'nt' and not os.access(paths['binary'], os.X_OK):
        raise ValueError('Piper executable does not have execute permission')
    return {'status': 'PIPER_HASHES_AND_OWNER_ATTESTATIONS_VERIFIED',
            'locale':locale, 'sample_rate':rate,
            'model':str(paths['model']), 'config':str(paths['config']), 'binary':str(paths['binary']),
            'model_sha256':profile['sha256'], 'config_sha256':profile['config_sha256'],
            'binary_sha256':profile['piper_binary_sha256'],
            'licence_independently_verified':False,'naturalness_accepted':False,
            'outbound_network_sandboxed':False}


def synthesize_piper_draft(profile: dict, locale: str, binary: Path, text: str,
                          output_wav: Path, *, ffmpeg: str | None = None,
                          timeout_seconds: int = 90) -> dict:
    """Invoke the explicitly hashed local Piper CLI once, normalize and QA audio.

    Never overwrite existing files; never run in a shell; never fetch models.
    Caller MUST review and listen before using a resulting narration draft.
    """
    checked = preflight_piper(profile, locale, binary)
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= MAX_TEXT_CHARS:
        raise ValueError('One bounded nonempty narration segment (max 650 chars) required')
    split_words(text)
    if any(ord(char) < 32 and char not in '\n\t' for char in text):
        raise ValueError('Unsafe voice input control character')
    if locale == 'hi-IN' and not any('\u0900' <= ch <= '\u097f' for ch in text):
        raise ValueError('Hindi input requires Devanagari text for verified Hindi voice')
    if type(timeout_seconds) is not int or not 5 <= timeout_seconds <= 180:
        raise ValueError('Invalid bounded synthesis timeout')
    output = Path(output_wav).expanduser()
    if output.suffix.lower() != '.wav' or output.is_symlink() or output.exists():
        raise ValueError('New, non-symlink WAV output path required; overwrites prohibited')
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError('Existing non-symlink output directory required')
    target = output.resolve(strict=False)
    if target in {Path(checked['model']),Path(checked['config']),Path(checked['binary'])}:
        raise ValueError('Do not overwrite Piper components')
    converter = ffmpeg or shutil.which('ffmpeg')
    if not converter:
        raise RuntimeError('Locally installed FFmpeg required')
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='viral-piper-', dir=str(output.parent)) as temp:
        scratch = Path(temp)
        original = scratch / 'native.wav'
        normalized = scratch / 'normalized.wav'
        env = dict(os.environ)
        env.update({'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','PIPER_OFFLINE':'1',
                    'PIP_DISABLE_PIP_VERSION_CHECK':'1'})
        # This is not an OS network sandbox; third-party binaries require owner trust.
        cmd = [checked['binary'],'--model',checked['model'],'--config',checked['config'],
               '--output_file',str(original)]
        try:
            process = subprocess.run(cmd,input=text+'\n',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True,
                                     env=env,cwd=str(scratch),timeout=timeout_seconds,check=False)
        except subprocess.TimeoutExpired as ex:
            raise RuntimeError('Local Piper synthesis timed out; no draft accepted') from ex
        if process.returncode != 0:
            raise RuntimeError(f'Local Piper exited with status {process.returncode}; inspect trusted local binary')
        if original.is_symlink() or not original.is_file() or not 0 < original.stat().st_size <= MAX_WAV_BYTES:
            raise ValueError('Piper did not generate a bounded regular WAV')
        try:
            conv = subprocess.run([str(converter),'-nostdin','-hide_banner','-loglevel','error','-y',
                                   '-i',str(original),'-map','0:a:0','-ac','1','-ar','16000',
                                   '-c:a','pcm_s16le',str(normalized)],capture_output=True,
                                  timeout=45,check=False)
        except subprocess.TimeoutExpired as ex:
            raise RuntimeError('Offline audio conversion timed out') from ex
        if conv.returncode != 0 or normalized.is_symlink() or not normalized.is_file() or normalized.stat().st_size > MAX_WAV_BYTES:
            raise ValueError('FFmpeg could not create valid 16kHz mono PCM16 audio')
        quality = wav_audio_qa(normalized)
        if quality['technical_flags']:
            raise ValueError('Technical audio QA blocked: '+','.join(quality['technical_flags']))
        if not 500 <= quality['duration_ms'] <= MAX_SECONDS * 1000:
            raise ValueError('Invalid narrator output duration')
        # O_EXCL denies overwriting if another process raced to create output.
        created = False
        try:
            with output.open('xb') as dest, normalized.open('rb') as src:
                created = True
                shutil.copyfileobj(src, dest, length=1024*1024)
        except Exception:
            if created:
                output.unlink(missing_ok=True)
            raise
    return {'status':'DRAFT_SYNTHESIZED_OWNER_LISTENING_REQUIRED',
            'locale':locale,'text_sha256':hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'model_sha256':checked['model_sha256'],
            'config_sha256':checked['config_sha256'],
            'binary_sha256':checked['binary_sha256'],
            'audio_sha256':sha256_file(output),'audio_qa':quality,
            'elapsed_seconds':round(time.monotonic()-start,3),
            'downloaded_model':False,'network_calls_by_viral_os':False,
            'third_party_executable_network_sandboxed':False,
            'naturalness_accepted':False,'rights_independently_certified':False,
            'can_auto_publish':False}
