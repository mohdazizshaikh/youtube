"""Deterministic, evidence-bound **manual** dubbing scene retimer.

Retime original graphics to owner-heard scene boundaries against the *actual*
localized narration WAV. No automatic speech recognition, translation, voice
cloning, phoneme timing, speech rate changes or guessed subtitle timestamps.
Captions remain owner-timed. The generated StudioPlan is still only a
watermarked technical preview until separate human editorial approval.
"""
from __future__ import annotations
import copy
import json

MAX_SCENE_CUES = 12


def retime_reviewed_plan(plan: dict, scene_ends: list[int], audio_ms: int) -> tuple[dict, dict]:
    """Retime scene lengths and within-scene overlays; never warp captions.

    `scene_ends` are owner-verified cumulative cue points in milliseconds.
    The last must match an independently measured 16kHz WAV within 250ms.
    A caption is rejected if it crosses a new scene boundary.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get('shots'), list):
        raise ValueError('Studio plan with shots required')
    count = len(plan['shots'])
    if not 2 <= count <= MAX_SCENE_CUES or not isinstance(scene_ends,list) or len(scene_ends)!=count:
        raise ValueError('One owner-verified cumulative audio cue per scene required')
    if type(audio_ms) is not int or audio_ms <= 0 or audio_ms > 90_000:
        raise ValueError('Measured narration duration must fit CPU preview cap')
    if any(type(v) is not int for v in scene_ends):
        raise ValueError('Scene boundaries must be integer milliseconds')
    if abs(scene_ends[-1]-audio_ms)>250:
        raise ValueError('Last owner scene cue disagrees with measured WAV duration')
    begins=[0]+scene_ends[:-1]
    durations=[end-start for start,end in zip(begins,scene_ends)]
    if any(not 1200<=d<=12000 for d in durations) or any(d<=0 for d in durations):
        raise ValueError('Owner scene cue outside 1.2–12 seconds per scene')
    new=copy.deepcopy(plan)
    for scene,expected in zip(new['shots'],durations):
        prev=scene.get('duration_ms')
        if type(prev) is not int or not 1200<=prev<=12000:
            raise ValueError('Invalid original scene length')
        # Narrative scenes cannot be stretched beyond 2.5x without editorial rethink.
        if expected > 2.5*prev or prev > 2.5*expected:
            raise ValueError('Severe scene retiming needs manual scene reauthoring')
        scene['duration_ms']=expected
        for overlay in scene.get('overlays',[]):
            start,end=overlay.get('start_ms'),overlay.get('end_ms')
            if type(start) is not int or type(end) is not int or end<=start or start<0 or end>prev:
                raise ValueError('Invalid original overlay timing')
            # Scale timing with deterministic integer arithmetic.
            overlay['start_ms']=(start*expected)//prev
            overlay['end_ms']=min(expected, max(overlay['start_ms']+1,(end*expected+prev//2)//prev))
    caps=new.get('captions',[])
    if new.get('captions_provenance')!='OWNER_TIMED' or not isinstance(caps,list) or not caps:
        raise ValueError('Owner-timed narration captions required for dubbing preview')
    for c in caps:
        start,end=c.get('start_ms'),c.get('end_ms')
        if type(start) is not int or type(end) is not int or not 0<=start<end<=scene_ends[-1]:
            raise ValueError('Owner caption timing outside measured narration timeline')
        if not any(b<=start and end<=e for b,e in zip(begins,scene_ends)):
            raise ValueError('Owner caption crosses new scene boundary; manually re-time text')
    return new, {'method':'OWNER_VERIFIED_AUDIO_CUES_DETERMINISTIC_SCENE_RETIME',
                 'source_duration_ms':sum(s['duration_ms'] for s in plan['shots']),
                 'measured_audio_duration_ms':audio_ms,'scene_end_ms':scene_ends,
                 'adjusted_scene_durations_ms':durations,
                 'caption_timestamps_guessed':False,'source_audio_retimed':False,
                 'automatic_translation_or_dubbing':False,'owner_final_approval':False}
