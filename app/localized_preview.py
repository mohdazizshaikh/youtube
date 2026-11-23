"""M2.5 offline, owner-provided bilingual localized CPU technical preview.

This is NOT text-to-speech, translation, voice cloning, word alignment,
final owner approval, or a publishing route. Every caption is owner timed and
must literally reproduce the reviewed localized text; on-screen headings are
bound to the reviewed variant, not independently invented.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from fastapi import UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import ValidationError

from . import db
from .localization_review import dependencies
from .m24_audio import wav_audio_qa
from .studio_contracts import StudioPlanIn
from .studio_render import render_studio
from .studio_routes import sha_file

MAX_VOICE_BYTES = 12 * 1024 * 1024
MAX_PLAN_CHARS = 50_000


def reviewed_variant(c, project_id: str, variant_id: str):
    from . import main as m
    project = m.from_project(c, project_id)
    script = m.latest_script(c, project_id)
    row = db.one(c, 'SELECT * FROM m25_localized_variants WHERE project_id=? AND variant_id=?',
                 (project_id, variant_id))
    if not row:
        raise HTTPException(404, 'Localized variant not found')
    if row['status'] != 'OWNER_REVIEWED':
        raise HTTPException(409, 'Localized script needs owner approval')
    if not script or script['script_version_id'] != row['script_version_id'] or \
            script['content_sha256'] != row['source_script_sha256'] or \
            dependencies(c, project_id, script) != row['dependency_sha256']:
        raise HTTPException(409, 'Localized script stale: source/evidence changed')
    return project, row, json.loads(row['content_json'])


def validated_plan(raw: str, variant: dict, content: dict) -> dict:
    if not isinstance(raw, str) or len(raw) > MAX_PLAN_CHARS:
        raise HTTPException(422, 'Localized plan JSON too large')
    try:
        model = StudioPlanIn.model_validate_json(raw)
    except (ValidationError, ValueError) as ex:
        raise HTTPException(422, 'Invalid localized StudioPlan: ' + str(ex)[:400]) from ex
    plan = model.model_dump(mode='json')
    if plan['locale'] != variant['locale'] or not plan['locale_reviewed']:
        raise HTTPException(409, 'Plan locale must match the owner-reviewed locale')
    if plan.get('music_asset_id'):
        raise HTTPException(409, 'M2.5 proof-of-concept supports narration only, not third-party music')
    if any(s['visual']['kind'] == 'RIGHTS_APPROVED_STILL' or
           any(o['style'] == 'IMAGE_INSERT' for o in s['overlays']) for s in plan['shots']):
        raise HTTPException(409, 'M2.5 proof-of-concept supports original diagrams only')
    screens = content['on_screen_text']
    if len(screens) != len(plan['shots']) or any(s['headline'] != t for s, t in zip(plan['shots'], screens)):
        raise HTTPException(409, 'Each shot headline must exactly match reviewed localized on-screen text')
    if plan['captions_provenance'] != 'OWNER_TIMED' or not plan['captions']:
        raise HTTPException(409, 'Owner-timed captions are compulsory for localized preview')
    # No unseen automatic translation or extra assertions in subtitle content.
    norm = lambda text: ' '.join(text.split()).casefold()
    if norm(' '.join(c['text'] for c in plan['captions'])) != norm(content['localized_script']):
        raise HTTPException(409, 'Caption transcript must equal reviewed localized script')
    return plan


def require_devanagari_font(locale: str) -> None:
    """Reject known Latin-only font fallback for a Hindi render.

    This is a conservative font-name preflight, NOT glyph-by-glyph visual QA.
    A native reader must still check text ligatures and safe areas in output.
    """
    if locale != 'hi-IN':
        return
    from .studio_render import font_file
    try:
        name=Path(font_file(locale)).stem.casefold().replace('-', '').replace('_', '')
    except (OSError, RuntimeError) as ex:
        raise HTTPException(409, 'Hindi requires a locally installed Devanagari font') from ex
    known=('nirmala','mangal','notosansdevanagari','lohitdevanagari','kalam','hind')
    if not any(name.startswith(x) for x in known):
        raise HTTPException(409, 'Hindi renderer selected an unverified Latin-only fallback font')


def register_localized_preview(app):
    from . import main as m

    @app.get('/api/m25/localized-preview/capabilities')
    def capabilities():
        return {'cpu_render':True,'owner_supplied_narration_pcm16_16khz':True,
                'owner_timed_captions':True,'localized_headlines_bound_to_review':True,
                'format_limit_ms':90000,'automatic_translation':False,
                'automatic_dubbing_or_tts':False,'automatic_word_alignment':False,
                'copyright_certified':False,'upload_eligible':False,
                'status':'TECHNICAL_PREVIEW_HUMAN_REVIEW_REQUIRED'}

    @app.post('/api/projects/{project_id}/m25/localizations/{variant_id}/studio-preview')
    async def preview(project_id: str, variant_id: str, file: UploadFile = File(...),
                      plan_json: str = Form(...), owner_voice_rights_attested: bool = Form(...),
                      voice_origin: str = Form(...)):
        if not owner_voice_rights_attested or len(voice_origin.strip()) < 8 or len(voice_origin) > 500:
            raise HTTPException(422, 'Owner must attest local narration provenance and permitted voice rights')
        with db.read() as c:
            project,variant,content = reviewed_variant(c,project_id,variant_id)
            plan = validated_plan(plan_json,variant,content)
            require_devanagari_font(plan['locale'])
            sport = project['sport_id'];fmt=project['format']
            source_hash=variant['dependency_sha256'];content_hash=variant['content_sha256']
        raw = await file.read(MAX_VOICE_BYTES + 1)
        if not raw or len(raw) > MAX_VOICE_BYTES or raw[:4] != b'RIFF' or raw[8:12] != b'WAVE':
            raise HTTPException(422, 'Owner narration must be a bounded 16kHz PCM16 WAV')
        folder = m.OUT / project_id / 'localized_previews' / m.uid()
        folder.mkdir(parents=True,exist_ok=False)
        wav = folder / 'owner_voice.wav'
        wav.write_bytes(raw)
        try:
            audio = wav_audio_qa(wav)
            if audio['technical_flags']:
                raise HTTPException(409, 'Narration technical QA failed: ' + ', '.join(audio['technical_flags']))
            try:
                video, quality, manifest = render_studio(plan,sport,fmt,{},wav,folder,release=False)
            except (ValueError,RuntimeError,OSError) as ex:
                raise HTTPException(422,'CPU localized preview failed: ' + str(ex)[:300]) from ex
            digest = sha_file(video)
            plan_sha = hashlib.sha256(m.j(plan).encode('utf8')).hexdigest()
            with db.transaction() as c:
                _,fresh, _ = reviewed_variant(c,project_id,variant_id)
                if fresh['dependency_sha256'] != source_hash or fresh['content_sha256'] != content_hash:
                    raise HTTPException(409,'Localization changed while rendering')
                preview_id=folder.name
                c.execute('INSERT INTO m25_localized_previews '
                          '(preview_id,project_id,variant_id,source_dependency_sha256,variant_content_sha256,'
                          'plan_sha256,voice_sha256,voice_origin,owner_voice_rights_attested,'
                          'preview_file_relpath,preview_file_sha256,quality_json,status,created_at) '
                          'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                          (preview_id,project_id,variant_id,source_hash,content_hash,plan_sha,audio['audio_sha256'],
                           voice_origin.strip(),1,str(video.relative_to(m.OUT)),digest,m.j(quality),
                           'TECHNICAL_PREVIEW_OWNER_REVIEW_REQUIRED',m.now()))
            return {'preview_id':preview_id,'status':'TECHNICAL_PREVIEW_OWNER_REVIEW_REQUIRED',
                    'download_url':f'/api/projects/{project_id}/m25/localized-previews/{preview_id}/download',
                    'sha256':digest,'duration_ms':manifest['total_duration_ms'],
                    'locale':plan['locale'],'audio_qa':audio,'automated_quality':quality['status'],
                    'translated_by_model':False,'narration_generated_by_model':False,
                    'word_alignment_performed':False,'owner_final_approval':False,
                    'youtube_upload_eligible':False}
        except Exception:
            shutil.rmtree(folder,ignore_errors=True)
            raise

    @app.get('/api/projects/{project_id}/m25/localized-previews/{preview_id}/download')
    def download(project_id:str,preview_id:str):
        with db.read() as c:
            row=db.one(c,'SELECT * FROM m25_localized_previews WHERE project_id=? AND preview_id=?',
                       (project_id,preview_id))
            if not row:raise HTTPException(404,'Localized preview not found')
            _, variant, _ = reviewed_variant(c, project_id, row['variant_id'])
            if variant['dependency_sha256']!=row['source_dependency_sha256'] or \
                    variant['content_sha256']!=row['variant_content_sha256']:
                raise HTTPException(409,'Localized preview is stale')
        path=(m.OUT/row['preview_file_relpath']).resolve()
        if m.OUT.resolve() not in path.parents or not path.is_file() or sha_file(path)!=row['preview_file_sha256']:
            raise HTTPException(409,'Localized preview missing or content modified')
        return FileResponse(path,media_type='video/mp4',filename='ViralOS_Localized_Technical_Preview_NOT_APPROVED.mp4')
