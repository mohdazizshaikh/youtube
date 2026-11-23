"""M2.4 fail-closed, local-only CTC model provenance verification.

The owner supplies model bytes AND an out-of-band local manifest. This code
checks exact file hashes and a rights-review attestation before an optional
acoustic model can be loaded. A signed license/legal opinion and natural voice
quality are NOT established by a manifest or by a successful file hash check.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from .m24_audio import SUPPORTED_LOCALES

MAX_MODEL_FILES = 200
MAX_MODEL_BYTES = 4 * 1024**3
_SHA = re.compile(r'^[0-9a-f]{64}$')
_ID = re.compile(r'^[A-Za-z0-9._-]{2,120}$')


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(1024*1024), b''):
            h.update(data)
    return h.hexdigest()


def _safe_relpath(value: str) -> bool:
    if not isinstance(value, str) or not value or '\\' in value:
        return False
    p = PurePosixPath(value)
    return not p.is_absolute() and str(p) == value and '..' not in p.parts and not any(x in ('', '.') for x in p.parts)


def inspect_ctc_model(model_dir: Path, manifest_path: Path, locale: str) -> dict:
    """Verify every local model-directory file without following links/network.

    The manifest is supplied from a separate owner-controlled location. A
    changed or unlisted model file refuses inference, not merely warns.
    """
    if locale not in SUPPORTED_LOCALES:
        raise ValueError('Unsupported CTC model locale')
    if Path(model_dir).is_symlink() or Path(manifest_path).is_symlink():
        raise ValueError('Symlink model roots/manifests forbidden')
    root = Path(model_dir).resolve(strict=True)
    manifest_file = Path(manifest_path).resolve(strict=True)
    if not root.is_dir() or not manifest_file.is_file() or manifest_file.is_symlink():
        raise ValueError('Existing model directory and manifest file required')
    if manifest_file.is_relative_to(root):
        raise ValueError('Model manifest must be stored outside the model directory')
    if manifest_file.stat().st_size > 128 * 1024:
        raise ValueError('Model manifest too large')
    manifest = json.loads(manifest_file.read_text(encoding='utf8'))
    if not isinstance(manifest, dict) or set(manifest) != {
        'schema','model_id','locale','license_reference','owner_rights_review_attested',
        'commercial_use_allowed_per_owner','files_sha256'
    }:
        raise ValueError('Malformed CTC provenance manifest')
    if manifest['schema'] != 'VIRALOS_LOCAL_CTC_MODEL_V1' or manifest['locale'] != locale:
        raise ValueError('Unsupported/mismatched CTC model manifest or locale')
    if not isinstance(manifest['model_id'], str) or not _ID.fullmatch(manifest['model_id']):
        raise ValueError('Unsafe or invalid model ID')
    if not isinstance(manifest['license_reference'], str) or not 12 <= len(manifest['license_reference'].strip()) <= 500:
        raise ValueError('Owner must record a specific local license reference')
    if manifest['owner_rights_review_attested'] is not True or manifest['commercial_use_allowed_per_owner'] is not True:
        raise ValueError('Owner rights review/commercial-use attestation not supplied')
    declared = manifest['files_sha256']
    if not isinstance(declared, dict) or not 2 <= len(declared) <= MAX_MODEL_FILES:
        raise ValueError('CTC model must declare a bounded nonempty file manifest')
    if 'config.json' not in declared or not any(
        PurePosixPath(x).name == 'model.safetensors' or PurePosixPath(x).name == 'pytorch_model.bin'
        or re.fullmatch(r'model-\d{5}-of-\d{5}\.safetensors', PurePosixPath(x).name)
        for x in declared
    ):
        raise ValueError('CTC model needs config.json and local weight files')
    for path, sha in declared.items():
        if not _safe_relpath(path) or not isinstance(sha, str) or not _SHA.fullmatch(sha):
            raise ValueError('Unsafe manifest file path or SHA-256')
    found = {}
    total = 0
    for file in root.rglob('*'):
        if file.is_symlink():
            raise ValueError('Symlink in model directory prohibited')
        if not file.is_file():
            continue
        relative = file.relative_to(root).as_posix()
        if not _safe_relpath(relative) or relative not in declared:
            raise ValueError('Unlisted/unsafe model file: ' + relative)
        size = file.stat().st_size
        total += size
        if size > MAX_MODEL_BYTES or total > MAX_MODEL_BYTES:
            raise ValueError('Local model file-size budget exceeded')
        sha = _digest(file)
        if sha != declared[relative]:
            raise ValueError('Local model SHA-256 mismatch: ' + relative)
        found[relative] = sha
        if len(found) > MAX_MODEL_FILES:
            raise ValueError('Model directory has too many files')
    if set(found) != set(declared):
        raise ValueError('Declared model files missing: ' + ', '.join(sorted(set(declared)-set(found)))[:250])
    return {
        'status': 'LOCAL_CTC_MODEL_HASHES_VERIFIED_RIGHTS_OWNER_ATTESTED',
        'model_id': manifest['model_id'], 'locale': locale,
        'manifest_sha256': _digest(manifest_file), 'files_verified': len(found),
        'bytes_verified': total, 'license_reference': manifest['license_reference'],
        'remote_download_performed': False, 'inference_performed': False,
        'license_independently_verified': False, 'human_speech_quality_accepted': False,
        'model_alignment_benchmark_accepted': False,
    }
