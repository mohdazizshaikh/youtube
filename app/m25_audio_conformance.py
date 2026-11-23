"""Bounded, offline audio-track comparison for owner-supplied narration WAV/MP4.

This is a conservative sampled waveform correlation check, NOT voice recognition,
transcription, speaker identity, or proof that every spoken word is correct.
AAC re-encoding and loud music may create false negatives; never auto-publish.
"""
from __future__ import annotations

from array import array
import math
from pathlib import Path
import shutil
import subprocess
import sys
import wave

MAX_AUDIO_SECONDS = 120
PCM_RATE = 16000
STRIDE = 16  # 1 kHz fixed, deterministic sample grid
MATCH_THRESHOLD = 0.65
MIN_COVERAGE = 0.80


def _mono_pcm16_wav(path: Path) -> array:
    with wave.open(str(path), 'rb') as wf:
        if (wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getcomptype()) != (1, 2, PCM_RATE, 'NONE'):
            raise ValueError('Narration must be 16kHz mono PCM16 WAV')
        n = wf.getnframes()
        if not PCM_RATE // 2 <= n <= PCM_RATE * MAX_AUDIO_SECONDS:
            raise ValueError('Narration duration must be 0.5–120 seconds')
        result = array('h')
        result.frombytes(wf.readframes(n))
        if sys.byteorder != 'little':
            result.byteswap()
        if len(result) != n:
            raise ValueError('Damaged narration WAV')
        return result


def _decoded_track(video: Path, ffmpeg: str | None) -> array:
    executable = ffmpeg or shutil.which('ffmpeg')
    if not executable:
        raise ValueError('FFmpeg required for actual MP4 audio comparison')
    try:
        # No shell and no network input. The caller verifies a local hashed MP4.
        result = subprocess.run([
            str(executable), '-nostdin', '-hide_banner', '-loglevel', 'error',
            '-protocol_whitelist', 'file,pipe', '-i', str(video), '-map', '0:a:0', '-vn', '-sn',
            '-t', str(MAX_AUDIO_SECONDS), '-ac', '1', '-ar', str(PCM_RATE),
            '-f', 's16le', 'pipe:1'],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=45)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError('FFmpeg failed to decode first MP4 audio track') from exc
    max_bytes = PCM_RATE * 2 * MAX_AUDIO_SECONDS
    if result.returncode or not 16000 <= len(result.stdout) <= max_bytes or len(result.stdout) % 2:
        raise ValueError('MP4 has no usable bounded first audio track')
    audio = array('h')
    audio.frombytes(result.stdout)
    if sys.byteorder != 'little':
        audio.byteswap()
    return audio


def _waveform_score(original: array, output: array) -> tuple[float, int, float]:
    """Pearson correlation over 12 distributed 120 ms windows, +/- 400 ms lag.

    Each lag is sampled every 2 ms at 1 kHz. Exact AAC byte equality is
    impossible; a high sampled correlation provides *supporting* evidence only.
    """
    ref = original[::STRIDE]
    got = output[::STRIDE]
    window = 120
    if len(ref) < 500 or len(got) < 500:
        raise ValueError('Audio comparison requires at least half a second')
    starts = [round(i * (len(ref) - window) / 11) for i in range(12)]
    indices = [start + k for start in starts for k in range(window)]
    ref_sum = sum(ref[i] for i in indices)
    ref_sq = sum(ref[i] * ref[i] for i in indices)
    count_expected = len(indices)
    if ref_sq - (ref_sum * ref_sum / count_expected) < 1000:
        return 0.0, 0, 0.0
    best = (0.0, 0, 0.0)
    for lag in range(-400, 401, 2):
        pairs = [(i, i + lag) for i in indices if 0 <= i + lag < len(got)]
        coverage = len(pairs) / count_expected
        if coverage < MIN_COVERAGE:
            continue
        count = len(pairs)
        sx = sy = sxx = syy = sxy = 0
        for i, j in pairs:
            x, y = int(ref[i]), int(got[j])
            sx += x; sy += y; sxx += x * x; syy += y * y; sxy += x * y
        vx = sxx - sx * sx / count
        vy = syy - sy * sy / count
        if vx <= 0 or vy <= 0:
            continue
        score = (sxy - sx * sy / count) / math.sqrt(vx * vy)
        if score > best[0]:
            best = (score, lag, coverage)
    return best


def compare_narration_to_video(voice_wav: Path, mp4: Path, *, ffmpeg: str | None = None) -> dict:
    original = _mono_pcm16_wav(Path(voice_wav))
    output = _decoded_track(Path(mp4), ffmpeg)
    score, lag, coverage = _waveform_score(original, output)
    passed = score >= MATCH_THRESHOLD and coverage >= MIN_COVERAGE
    return {
        'method': 'SAMPLED_PCM_CORRELATION_FFMPEG_FIRST_AUDIO_TRACK_V1',
        'acoustically_consistent': passed,
        'max_normalized_correlation': round(score, 4),
        'estimated_audio_offset_ms': lag,
        'sampled_coverage': round(coverage, 3),
        'minimum_correlation': MATCH_THRESHOLD,
        'exact_reviewed_voice_proven': False,
        'speech_content_or_speaker_identity_verified': False,
        'human_listening_still_required': True,
        'external_network_used': False,
    }
