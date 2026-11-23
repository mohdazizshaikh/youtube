"""M2.4 offline audio director primitives.

Real CTC Viterbi forced alignment consumes acoustic model frame log-probabilities
and exact transcript tokens. Unlike heuristic equal-split timestamps, token
boundaries come from the acoustic emissions. The forced transcript is *not*
proof of what was actually spoken. Human review is always required.

No model downloading, speech cloning, OAuth, translation or publishing here.
"""
from __future__ import annotations

import hashlib
import math
import re
import struct
import wave
from pathlib import Path
from typing import Sequence

MAX_FRAMES = 4_000
MAX_TOKENS = 480
MAX_WORDS = 150
SUPPORTED_LOCALES = frozenset({'en-US', 'en-IN', 'hi-IN'})


def split_words(text: str) -> list[str]:
    """Unicode-preserving words: Devanagari diacritics remain attached."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError('Non-empty transcript required')
    words = text.strip().split()
    if len(words) > MAX_WORDS:
        raise ValueError('Too many words: align one short narration segment at a time')
    if any(len(word) > 90 or any(ord(c) < 32 for c in word) for word in words):
        raise ValueError('Invalid transcript word or control character')
    return words


def prefix_token_groups(tokenizer, words: Sequence[str], blank_id: int) -> tuple[list[int], list[tuple[int, int]]]:
    """Assign incremental prefix-stable CTC tokens to each original word.

    This supports tokenizer-specific word separator symbols without assuming
    that Latin-character splitting also works for Hindi. Reject unstable/BPE
    tokenizers and any unknown/blank transcript token, instead of fabricating
    alignment timestamps.
    """
    targets: list[int] = []
    groups: list[tuple[int, int]] = []
    unknown = getattr(tokenizer, 'unk_token_id', None)
    for index in range(1, len(words) + 1):
        full = tokenizer(' '.join(words[:index]), add_special_tokens=False)
        ids = full['input_ids'] if isinstance(full, dict) else full.input_ids
        if ids and isinstance(ids[0], list):
            raise ValueError('Tokenizer returned a batch; pass one transcript')
        ids = [int(t) for t in ids]
        if ids[:len(targets)] != targets:
            raise ValueError('Tokenizer is not prefix-stable: CTC word boundaries cannot be assigned')
        added = ids[len(targets):]
        if not added:
            raise ValueError('Transcript contains a word without CTC tokens')
        if any(t == blank_id or (unknown is not None and t == unknown) or t < 0 for t in added):
            raise ValueError('Transcript has blank/unknown CTC tokens; check locale and model vocabulary')
        groups.append((len(targets), len(ids)))
        targets = ids
    if not targets or len(targets) > MAX_TOKENS:
        raise ValueError('CTC transcript too long for bounded offline alignment')
    return targets, groups


def ctc_viterbi(log_probs: Sequence[Sequence[float]], targets: Sequence[int], blank: int) -> list[tuple[int, int, float]]:
    """Viterbi alignment on CTC's blank-extended state graph.

    Args:
      log_probs: T x K acoustic frame log probabilities (natural log).
      targets: 1..480 nonblank token IDs, valid indices into K.
      blank: blank-token ID.
    Returns one (start_frame, end_exclusive_frame, mean_acoustic_probability)
    per transcript token. Repeated identical tokens require an intervening
    blank state, as required by CTC.
    """
    tokens = list(targets)
    T = len(log_probs)
    if not tokens or len(tokens) > MAX_TOKENS or T < len(tokens) or T > MAX_FRAMES:
        raise ValueError('CTC frame/token bounds exceeded or no valid alignment possible')
    K = len(log_probs[0]) if T else 0
    if K < 2 or blank < 0 or blank >= K or any(t == blank or t < 0 or t >= K for t in tokens):
        raise ValueError('Invalid blank, vocabulary or CTC token IDs')
    if any(len(row) != K or any(not math.isfinite(v) or v > 0.00001 for v in row) for row in log_probs):
        raise ValueError('Every frame must contain same-size, finite log probabilities <= 0')
    states: list[int] = [blank]
    for t in tokens:
        states.extend([t, blank])
    N = len(states)
    prev = [-math.inf] * N
    prev[0] = log_probs[0][blank]
    prev[1] = log_probs[0][tokens[0]]
    back: list[list[int]] = [[-1] * N]
    for frame in range(1, T):
        current = [-math.inf] * N
        moves = [-1] * N
        row = log_probs[frame]
        for state in range(N):
            best_state = state
            best_score = prev[state]
            if state > 0 and prev[state - 1] > best_score:
                best_state, best_score = state - 1, prev[state - 1]
            if state > 1 and states[state] != blank and states[state] != states[state - 2] and prev[state - 2] > best_score:
                best_state, best_score = state - 2, prev[state - 2]
            if best_score != -math.inf:
                current[state] = best_score + row[states[state]]
                moves[state] = best_state
        back.append(moves)
        prev = current
    finish = N - 1 if prev[N - 1] >= prev[N - 2] else N - 2
    if prev[finish] == -math.inf:
        raise ValueError('CTC transcript incompatible with available acoustic frames')
    path = [finish]
    for frame in range(T - 1, 0, -1):
        finish = back[frame][finish]
        if finish < 0:
            raise ValueError('CTC alignment traceback impossible')
        path.append(finish)
    path.reverse()
    positions: list[list[int]] = [[] for _ in tokens]
    for frame, state in enumerate(path):
        if state % 2:
            positions[state // 2].append(frame)
    if any(not p for p in positions):
        raise ValueError('A transcript token has no acoustic alignment')
    return [
        (p[0], p[-1] + 1,
         round(sum(math.exp(log_probs[frame][tok]) for frame in p) / len(p), 5))
        for p, tok in zip(positions, tokens)
    ]


def word_intervals(words: Sequence[str], groups: Sequence[tuple[int, int]], spans: Sequence[tuple[int, int, float]],
                   audio_ms: int, frame_count: int) -> list[dict]:
    """Convert actual acoustic token intervals into word timestamps."""
    if len(words) != len(groups) or audio_ms <= 0 or frame_count <= 0:
        raise ValueError('Invalid word mapping or audio duration')
    out = []
    prev_end = 0
    for word, (lo, hi) in zip(words, groups):
        if lo >= hi or hi > len(spans):
            raise ValueError('Invalid word token span')
        selected = spans[lo:hi]
        start = round(selected[0][0] * audio_ms / frame_count)
        end = round(selected[-1][1] * audio_ms / frame_count)
        # A CTC delimiter token may be part of the current word; boundaries
        # must never run backward or overlap adjacent caption words.
        start = max(prev_end, start)
        end = min(audio_ms, max(start + 1, end))
        if start >= end:
            raise ValueError('CTC word timing collapsed; inspect audio and transcript')
        out.append({'token': word, 'start_ms': start, 'end_ms': end,
                    'acoustic_score': round(sum(x[2] for x in selected) / len(selected), 5)})
        prev_end = end
    return out


def wav_audio_qa(path: Path) -> dict:
    """Bounded 16kHz mono PCM16 inspection, without reading huge WAV into RAM.

    Acoustic quality metrics are technical diagnostics, not professional voice
    certification. No normalized voice or copyrighted media is generated.
    """
    p = Path(path)
    if not p.is_file() or p.stat().st_size > 40 * 1024 * 1024:
        raise ValueError('Audio missing or larger than 40 MiB')
    with wave.open(str(p), 'rb') as wf:
        if (wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getcomptype()) != (1, 2, 16000, 'NONE'):
            raise ValueError('WAV must be 16kHz mono uncompressed PCM16')
        frames = wf.getnframes()
        if frames < 8000 or frames > 16000 * 120:
            raise ValueError('WAV duration must be 0.5–120 seconds')
        sum_square = 0
        peak = 0
        clipped = 0
        near_silent = 0
        count = 0
        while count < frames:
            data = wf.readframes(min(8192, frames - count))
            if not data or len(data) % 2:
                raise ValueError('Damaged PCM16 WAV')
            samples = struct.unpack('<' + 'h' * (len(data) // 2), data)
            for s in samples:
                a = abs(s)
                peak = max(peak, a)
                clipped += int(a >= 32760)
                near_silent += int(a < 130)
                sum_square += s * s
            count += len(samples)
        if count != frames:
            raise ValueError('WAV truncated')
    rms = math.sqrt(sum_square / frames) / 32768
    score = {'duration_ms': round(frames * 1000 / 16000),
             'sample_rate_hz': 16000,
             'peak_dbfs': round(20 * math.log10(max(peak, 1) / 32768), 2),
             'rms_dbfs': round(20 * math.log10(max(rms, 1e-10)), 2),
             'clipped_fraction': round(clipped / frames, 6),
             'near_silent_fraction': round(near_silent / frames, 6),
             'audio_sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    issues = []
    if rms < 0.006: issues.append('LOW_SIGNAL_RMS')
    if clipped / frames > 0.001: issues.append('POSSIBLE_CLIPPING')
    if near_silent / frames > 0.95: issues.append('MOSTLY_SILENCE')
    score['technical_flags'] = issues
    score['review_required'] = True
    return score


def validate_voice_profile(profile: dict, locale: str) -> dict:
    """A strictly local voice selection/rights gate; no external voice downloads.

    A verified file hash is provenance only, not proof of voice licensing.
    """
    if locale not in SUPPORTED_LOCALES or not isinstance(profile, dict):
        raise ValueError('Locale unsupported by M2.4 voice preflight')
    if profile.get('locale') != locale or profile.get('backend') != 'piper':
        raise ValueError('Voice model locale/backend mismatch')
    if profile.get('rights_attested') is not True or not str(profile.get('license_reference', '')).strip():
        raise ValueError('Model license and voice-use rights must be owner-attested')
    if profile.get('cloned_voice') is True and profile.get('speaker_consent') is not True:
        raise ValueError('Voice clone requires speaker consent')
    model = Path(str(profile.get('model_file', ''))).expanduser()
    if (model.is_symlink() or model.suffix != '.onnx' or not model.is_file() or
            not 16 <= model.stat().st_size <= 4 * 1024**3):
        raise ValueError('Existing bounded, non-symlink local Piper .onnx model required')
    # A full voice model can be gigabytes; never load it entirely into RAM.
    hasher = hashlib.sha256()
    with model.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
    digest = hasher.hexdigest()
    if profile.get('sha256') != digest:
        raise ValueError('Local voice model SHA-256 differs from registered voice profile')
    return {'available': True, 'backend': 'piper', 'locale': locale,
            'model_sha256': digest, 'license_reference': profile['license_reference'],
            'rights_reviewed_by_owner': True, 'naturalness_human_accepted': False,
            'requires_sample_listening': True}
