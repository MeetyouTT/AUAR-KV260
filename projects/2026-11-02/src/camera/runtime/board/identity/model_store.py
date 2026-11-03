"""Explicit, isolated database selection for the INT8 SFace candidate.

Configuration validation is read-only. Opening the selected candidate service
creates its own 0600 database; the Windows configuration/database is untouched.
"""
import json
import os
from pathlib import Path
import sqlite3

MODEL_ID = 'sface-int8-12b2ff5c7de15713'
MODEL_SHA256 = '12b2ff5c7de157133ebd5aa71665fc5ddcd1f65d9e30e2d6e965e0752e467f25'
WINDOWS_MODEL_ID = 'sface-2021dec-0ba9fbfa01b5'
FINGERPRINT = '0x101000056010407'


def validate_dpu_configuration(config):
    backend = config.get('feature_backend')
    required = {'kind', 'model', 'manifest', 'model_sha256', 'manifest_sha256',
                'fallback_config', 'max_source_age_ms'}
    if (not isinstance(backend, dict) or set(backend) != required or backend['kind'] != 'dpu_sface'
            or config.get('model_id') != MODEL_ID or backend['model_sha256'] != MODEL_SHA256):
        raise ValueError('DPU SFace requires its exact versioned model configuration')
    if (type(backend['max_source_age_ms']) is not int
            or not 100 <= backend['max_source_age_ms'] <= min(1500, config['result_ttl_ms'])):
        raise ValueError('Invalid DPU SFace source lifetime')
    digest = backend['manifest_sha256']
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('An explicit SFace compiler manifest SHA256 is required')
    for key in ('model', 'manifest', 'fallback_config'):
        if not isinstance(backend[key], str) or not Path(backend[key]).is_absolute():
            raise ValueError('DPU SFace paths must be explicit absolute paths')
    database = Path(config['database']).expanduser()
    if not database.is_absolute() or MODEL_ID not in database.name:
        raise ValueError('DPU SFace requires a separate version-named database')
    fallback = json.loads(Path(backend['fallback_config']).read_text(encoding='utf-8'))
    remote = fallback.get('feature_backend')
    if (fallback.get('schema_version') != 'aura-camera-identity-1'
            or fallback.get('model_id') != WINDOWS_MODEL_ID
            or not isinstance(remote, dict) or remote.get('kind') != 'windows_sface'
            or remote.get('host') != '192.168.50.1' or remote.get('port') != 8792):
        raise ValueError('Fallback must preserve the original Windows FP32 configuration')
    legacy = Path(fallback['database']).expanduser()
    if not legacy.is_absolute() or database.resolve() == legacy.resolve():
        raise ValueError('INT8 and Windows identity databases must be separate')
    if database.exists() and legacy.exists() and os.path.samefile(str(database), str(legacy)):
        raise ValueError('INT8 database aliases the Windows database')
    photos = config.get('enrollment_photos')
    if photos and photos.get('enabled'):
        archive = Path(photos['directory']).expanduser()
        old_photos = fallback.get('enrollment_photos')
        if not archive.is_absolute() or MODEL_ID not in archive.name:
            raise ValueError('INT8 enrollment photos require a separate version-named archive')
        if old_photos and archive.resolve() == Path(old_photos['directory']).expanduser().resolve():
            raise ValueError('INT8 and Windows enrollment archives must be separate')
    validate_existing_database(database)


def check_artifact_configuration(config):
    """File/configuration check only; no XIR, VART, owner, device, or DB write."""
    import hashlib
    validate_dpu_configuration(config)
    backend = config['feature_backend']
    for key in ('model', 'manifest'):
        if hashlib.sha256(Path(backend[key]).read_bytes()).hexdigest() != backend[key+'_sha256']:
            raise ValueError('Pinned SFace artifact mismatch: '+key)
    manifest = json.loads(Path(backend['manifest']).read_text(encoding='utf-8'))
    dpu = [p for p in manifest['partitions'] if p['device'] == 'DPU']
    if (manifest['sha256'] != MODEL_SHA256 or len(dpu) != 1 or dpu[0]['fingerprint'] != FINGERPRINT
            or len(dpu[0]['inputs']) != 1 or len(dpu[0]['outputs']) != 1):
        raise ValueError('Unexpected SFace compiler manifest')
    source, result = dpu[0]['inputs'][0], dpu[0]['outputs'][0]
    if (source['dims'] != [1,112,112,3] or source['dtype'] != 'xint8' or source['fix_point'] != 7
            or result['dims'] != [1,128] or result['dtype'] != 'xint8' or result['fix_point'] != 5):
        raise ValueError('Unexpected SFace manifest tensor contract')
    import math
    threshold = config.get('threshold')
    margin = config.get('ambiguity_margin')
    threshold_configured = (type(threshold) in (int, float) and math.isfinite(threshold)
                            and 0 <= threshold <= 1 and type(margin) in (int, float)
                            and math.isfinite(margin) and 0 <= margin <= 1)
    return {'status':'CONFIG_VALIDATED_NOT_RUNTIME_TESTED', 'backend':'DPU_SFACE_INT8',
            'model_id':MODEL_ID, 'model_sha256':MODEL_SHA256, 'fingerprint':FINGERPRINT,
            'database_opened':False, 'database_created':False, 'runner_created':False,
            'threshold_configured':threshold_configured, 'field_threshold_validated':False,
            'fallback':'EXPLICIT_WHOLE_CONFIG_ROLLBACK'}


def validate_existing_database(path):
    """Reject a renamed, mixed, or unbound existing database before any write."""
    path = Path(path)
    # exists() is false for a dangling symlink. Reject it explicitly so SQLite
    # cannot create a database through an unreviewed filesystem alias.
    if path.is_symlink():
        raise ValueError('INT8 identity database must be a real file, not a symlink')
    if not path.exists():
        return
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError('Existing INT8 database must have a valid model binding')
    connection = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        binding = connection.execute('SELECT model_id, dimension FROM identity_model_binding').fetchall()
        if binding != [(MODEL_ID, 128)]:
            raise ValueError('INT8 identity database model binding mismatch')
        foreign = connection.execute('SELECT DISTINCT model_id, dimension FROM templates').fetchall()
        if any(row != (MODEL_ID, 128) for row in foreign):
            raise ValueError('Foreign templates in INT8 identity database')
    except sqlite3.Error as exc:
        raise ValueError('Existing database is not a bound INT8 identity database') from exc
    finally:
        connection.close()


def open_dpu_store(config):
    """Called only after the user explicitly selects the DPU service config."""
    from board.identity.store import IdentityStore
    validate_dpu_configuration(config)
    path = Path(config['database'])
    path.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        # Revalidate after file creation races; never adopt an unbound file.
        validate_existing_database(path)
    else:
        os.close(fd)
        created = True
    store = None
    try:
        store = IdentityStore(path, MODEL_ID, 128, config['threshold'], config['ambiguity_margin'],
                              allow_cross_thread=True)
        with store.db:
            if created:
                store.db.execute('CREATE TABLE identity_model_binding '
                                 '(model_id TEXT PRIMARY KEY, dimension INTEGER NOT NULL)')
                store.db.execute('INSERT INTO identity_model_binding VALUES (?, ?)', (MODEL_ID, 128))
        validate_existing_database(path)
        return store
    except Exception:
        if store is not None:
            store.close()
        # Retain an incomplete new file for explicit inspection; never delete
        # or overwrite any database during initialization failure.
        raise

