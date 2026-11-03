"""Explicit private migration receipt gate; never creates a store on startup.

Sealing writes only after an explicit single-writer handoff. Normal verification
is read-only. Production startup may let SQLite recover an uncommitted rollback
journal while both original writer leases are held. Origin/import markers remain
mandatory. No key, template, ID or text is returned.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat

SCHEMA = 'aura.board.production-bootstrap.v1'
ORIGIN_TABLE = 'bm_production_origin'
TARGETS = {'timeline':'timeline.sqlite3', 'speaker':'speaker/speakers.sqlite3',
           'anonymous_voice':'speaker/anonymous-voices.sqlite3', 'identity_links':'speaker/identity-links.sqlite3'}
APPLICATION_IDS = {'timeline':0x41555242, 'speaker':0x41555350,
                   'anonymous_voice':0x4155414E, 'identity_links':0x41554C4B}
ORIGIN_COLUMNS = {'slot','database_uuid','bundle_id','sources_sha256','migration_manifest_sha256'}
ORIGIN_DDL = ('CREATE TABLE bm_production_origin(slot INTEGER PRIMARY KEY CHECK(slot=1),'
              'database_uuid TEXT NOT NULL,bundle_id TEXT NOT NULL,sources_sha256 TEXT NOT NULL,'
              'migration_manifest_sha256 TEXT NOT NULL)')


class ProductionBootstrapRejected(ValueError):
    pass


def _fail(code):
    raise ProductionBootstrapRejected(code)


def _canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def _digest(value):
    if not isinstance(value,str) or re.fullmatch(r'[0-9a-f]{64}',value) is None:
        _fail('invalid_fingerprint')
    return value


def _hash(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda:stream.read(1024*1024),b''): value.update(part)
    return value.hexdigest()


def _private_root(root):
    root = Path(root).absolute()
    if (os.name != 'posix' or root.resolve(strict=True) != root or
            any(p.casefold()=='win共享文件' for p in root.parts)):
        _fail('canonical_board_private_root_required')
    info = root.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        _fail('private_root_owner_or_mode')
    return root


def _private_file(root, relative):
    rel = Path(relative)
    if rel.is_absolute() or '..' in rel.parts:
        _fail('relative_private_target_required')
    path = root/rel
    if path.resolve(strict=True) != path or root not in path.parents:
        _fail('private_target_redirect')
    for parent in path.parents:
        if parent == root: break
        info = parent.stat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            _fail('private_target_parent_mode')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        _fail('private_target_owner_or_mode')
    return path


def _db(path, write=False, *, recover=False):
    # Recovery uses SQLite's rollback handling. SQL remains query-only and a
    # missing production database is never created by either URI mode.
    mode = 'rw' if write or recover else 'ro'
    db = sqlite3.connect(path.as_uri()+'?mode='+mode,uri=True,timeout=.15,isolation_level=None)
    try:
        db.row_factory = sqlite3.Row
        if not write:
            db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
        return db
    except BaseException:
        db.close()
        raise


def _schema_hash(db, kind):
    # binding_invalidations is a known lazily-created original link table. Its
    # exact shape is checked, but its presence is not a permanent DB identity.
    rows = [tuple(r) for r in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")]
    if kind == 'identity_links':
        info = db.execute('PRAGMA table_info(binding_invalidations)').fetchall()
        if info and {r['name'] for r in info} != {'person_id','modality','reason','at'}:
            _fail('link_optional_schema_changed')
        rows = [r for r in rows if r[2] != 'binding_invalidations']
    return hashlib.sha256(_canonical(rows).encode()).hexdigest()


def _read_origin(db):
    info = db.execute('PRAGMA table_info(bm_production_origin)').fetchall()
    if {r['name'] for r in info} != ORIGIN_COLUMNS or [r['name'] for r in info if r['pk']] != ['slot']:
        _fail('origin_schema_missing_or_changed')
    rows = db.execute('SELECT * FROM bm_production_origin').fetchall()
    if len(rows)!=1 or rows[0]['slot']!=1:
        _fail('origin_marker_missing_or_changed')
    return dict(rows[0])


def _import_marker(db, table, item):
    if table not in ('bm_migrations','bm_observation_migrations'):
        _fail('unknown_import_marker')
    row = db.execute('SELECT * FROM '+table+' WHERE import_id=?',(item['import_id'],)).fetchone()
    if row is None or row['state']!='complete' or row['source_sha256']!=item['source_sha256']:
        _fail('required_import_marker_missing')
    return json.loads(row['report'])


def _conversation_selection(root, db, *, initial=False, import_id=None):
    path = root/'conversation_selection.json'
    if not path.exists(): return False,None
    path = _private_file(root,path.name)
    if path.stat().st_size>1024: _fail('invalid_conversation_selection')
    try: value=json.loads(path.read_bytes())
    except (ValueError,UnicodeError): _fail('invalid_conversation_selection')
    if (not isinstance(value,dict) or set(value)!={'version','conversation_id'} or
            type(value['version']) is not int or value['version']!=1 or
            not isinstance(value['conversation_id'],str) or re.fullmatch('[0-9a-f]{32}',value['conversation_id']) is None):
        _fail('invalid_conversation_selection')
    if not db.execute("SELECT 1 FROM bm_scopes WHERE kind='conversation' AND id=?",(value['conversation_id'],)).fetchone():
        _fail('saved_conversation_scope_missing')
    if initial and not db.execute("SELECT 1 FROM bm_migration_scope_meta WHERE import_id=? "
                                 "AND scope_kind='conversation' AND scope_id=? LIMIT 1",
                                 (import_id,value['conversation_id'])).fetchone():
        _fail('saved_conversation_not_in_source_map')
    return True,_hash(path)


def register_anonymous_conversation(store, conversation_id):
    """Register an empty anonymous scope before its selection is persisted.

    This issues no profile permission and does not select/merge other scopes.
    The runtime must already hold its normal board-private writer lease.
    """
    from .board_memory import BoardMemoryStore
    if (not isinstance(store,BoardMemoryStore) or store.data_origin!='board' or
            not isinstance(conversation_id,str) or re.fullmatch('[0-9a-f]{32}',conversation_id) is None):
        _fail('invalid_anonymous_conversation_scope')
    with store._db(True) as db:
        linked=db.execute("SELECT 1 FROM sqlite_master WHERE name='bm_migration_conversation_profiles'").fetchone()
        if linked and db.execute('SELECT 1 FROM bm_migration_conversation_profiles WHERE conversation_id=?',
                                 (conversation_id,)).fetchone():
            _fail('profile_conversation_cannot_be_anonymous')
        store._ensure_scope(db,('conversation',conversation_id))
    return dict(registered=True,scope_kind='conversation',profile_grants_issued=0)


def stage_initial_conversation_selection(store, root, source_path, *, import_id):
    """Copy an explicit private legacy selection only when its anonymous scope
    was imported. No guessed fallback, profile grant or cross-scope merge.
    """
    from .board_memory import BoardMemoryStore
    root=_private_root(root)
    if not isinstance(store,BoardMemoryStore) or store.data_origin!='board' or Path(store.path).parent!=root:
        _fail('board_target_store_required')
    source=Path(source_path).absolute()
    source=_private_file(_private_root(source.parent),source.name)
    if source.stat().st_size>1024:_fail('invalid_conversation_selection')
    try:value=json.loads(source.read_bytes())
    except (ValueError,UnicodeError):_fail('invalid_conversation_selection')
    if (not isinstance(value,dict) or set(value)!={'version','conversation_id'} or type(value['version']) is not int or
            value['version']!=1 or not isinstance(value['conversation_id'],str) or
            re.fullmatch('[0-9a-f]{32}',value['conversation_id']) is None):_fail('invalid_conversation_selection')
    with store._db() as db:
        if not db.execute("SELECT 1 FROM bm_scopes s JOIN bm_migration_scope_meta m ON m.scope_kind=s.kind AND m.scope_id=s.id "
                          "WHERE s.kind='conversation' AND s.id=? AND m.import_id=?",
                          (value['conversation_id'],import_id)).fetchone():
            _fail('saved_conversation_not_an_imported_anonymous_scope')
    target=root/'conversation_selection.json'
    encoded=(_canonical(value)+'\n').encode()
    if target.exists():
        _private_file(root,target.name)
        if json.loads(target.read_bytes())!=value:_fail('different_saved_conversation_already_exists')
        return dict(conversation_selection_verified=True,idempotent=True)
    fd=os.open(str(target),os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(encoded);stream.flush();os.fsync(stream.fileno())
    return dict(conversation_selection_verified=True,idempotent=False)


def _load_bootstrap_receipt(root, receipt_path, expected_sha256):
    """Check the pinned receipt and existing private paths before opening SQL."""
    root = _private_root(root)
    supplied = Path(receipt_path).absolute()
    if supplied.parent != root: _fail('receipt_must_be_at_private_root')
    receipt = _private_file(root,supplied.name)
    if receipt.stat().st_size>65536 or _hash(receipt)!=_digest(expected_sha256):
        _fail('receipt_fingerprint_mismatch')
    try: value = json.loads(receipt.read_bytes())
    except (ValueError,UnicodeError): _fail('invalid_receipt_json')
    required = {'schema','bundle_id','data_origin','private_root','initial_retention_enabled',
                'targets','imports','profiles_migration_verified','profiles_imported',
                'speaker_model_id','speaker_receipt_key_sha256','conversation_selection_verified',
                'conversation_selection_sha256'}
    if (not isinstance(value,dict) or set(value)!=required or value['schema']!=SCHEMA or
            value['data_origin']!='board' or value['private_root']!=str(root) or
            value['initial_retention_enabled'] is not False or value['profiles_migration_verified'] is not True or
            type(value['profiles_imported']) is not int or value['profiles_imported']<0 or
            re.fullmatch('[0-9a-f]{32}',value.get('bundle_id','')) is None or
            set(value['targets'])!=set(TARGETS) or set(value['imports'])!={'conversation','observation'}):
        _fail('receipt_schema_or_origin')
    if type(value['conversation_selection_verified']) is not bool:
        _fail('receipt_selection_proof_invalid')
    if value['conversation_selection_verified']:
        _digest(value['conversation_selection_sha256'])
    elif value['conversation_selection_sha256'] is not None:
        _fail('receipt_selection_proof_invalid')
    for kind, relative in TARGETS.items():
        if value['targets'][kind]['path'] != relative:
            _fail('unexpected_target_path')
        _private_file(root, relative)
    return root, value


def verify_production_bootstrap_receipt(root, receipt_path, expected_sha256):
    """Validate startup inputs without opening or recovering any database."""
    _load_bootstrap_receipt(root, receipt_path, expected_sha256)
    return dict(receipt_file_verified=True, database_contents_verified=False)


def _require_recovery_leases(root, leases):
    # Import only for the explicit production path to keep ordinary diagnostic
    # verification read-only and free of runtime construction.
    from board.runtime.board_business import _BoardWriterLock
    from board.runtime.board_speaker_business import _WriterLease
    if (type(leases) is not tuple or len(leases) != 2 or
            not isinstance(leases[0], _BoardWriterLock) or
            not isinstance(leases[1], _WriterLease)):
        _fail('startup_recovery_requires_original_writer_leases')
    for lease, directory, relative in (
            (leases[0], root, 'writer.lock'),
            (leases[1], root/'speaker', 'speaker/speaker-writer.lock')):
        if lease.fd is None or lease.root != directory:
            _fail('startup_recovery_writer_lease_mismatch')
        held = os.fstat(lease.fd)
        named = _private_file(root, relative).stat()
        if (held.st_dev, held.st_ino) != (named.st_dev, named.st_ino):
            _fail('startup_recovery_writer_lease_replaced')


def verify_production_bootstrap(root, receipt_path, expected_sha256, *, recovery_leases=None):
    """Verify the complete original origin/import/schema receipt.

    Ordinary callers stay read-only. The production constructor may request
    SQLite rollback recovery only under both original exclusive writer leases.
    initial_retention_enabled=False attests bootstrap policy only.
    """
    root, value = _load_bootstrap_receipt(root, receipt_path, expected_sha256)
    if recovery_leases is not None:
        _require_recovery_leases(root, recovery_leases)
    current_selection,current_selection_sha256=False,None
    for kind,relative in TARGETS.items():
        target = value['targets'][kind]
        if target['path']!=relative: _fail('unexpected_target_path')
        path = _private_file(root,relative)
        db = _db(path, recover=recovery_leases is not None)
        try:
            origin = _read_origin(db)
            if (origin['database_uuid']!=target['database_uuid'] or origin['bundle_id']!=value['bundle_id'] or
                    origin['sources_sha256']!=target['sources_sha256'] or
                    origin['migration_manifest_sha256']!=target['migration_manifest_sha256'] or
                    db.execute('PRAGMA application_id').fetchone()[0]!=APPLICATION_IDS[kind] or
                    db.execute('PRAGMA user_version').fetchone()[0]!=target['user_version'] or
                    _schema_hash(db,kind)!=target['schema_sha256'] or
                    db.execute('PRAGMA quick_check').fetchone()[0]!='ok'):
                _fail('target_origin_or_schema_changed')
            if kind == 'timeline':
                if db.execute("SELECT value FROM bm_meta WHERE key='data_origin'").fetchone()[0]!='board':
                    _fail('timeline_origin_changed')
                conversation = _import_marker(db,'bm_migrations',value['imports']['conversation'])
                _import_marker(db,'bm_observation_migrations',value['imports']['observation'])
                if conversation['profiles']!=value['profiles_imported'] or conversation['issued_profile_grants']!=0:
                    _fail('profile_migration_marker_changed')
                current_selection,current_selection_sha256 = _conversation_selection(root,db)
        finally: db.close()
    key = _private_file(root,'speaker/identity-link-receipt.key')
    if key.stat().st_size!=32 or _hash(key)!=value['speaker_receipt_key_sha256']:
        _fail('speaker_receipt_key_changed')
    # The owner marker can be serialized again by the local speaker owner.
    # Do not freeze a current epoch, gallery revision or profile count.
    owner = json.loads(_private_file(root,'speaker/speaker-business-owner.json').read_bytes())
    namespace = json.loads(_private_file(root,'speaker/speaker-gallery-namespace.json').read_bytes())
    if (owner.get('data_origin')!='board' or owner.get('origin')!='imported_snapshot' or
            owner.get('model_id')!=value['speaker_model_id'] or namespace.get('model_id')!=value['speaker_model_id'] or
            namespace.get('version')!=1):
        _fail('speaker_import_owner_changed')
    return dict(bundle_id=value['bundle_id'],data_origin='board',target_paths=dict(TARGETS),
                profiles_migration_verified=True,profiles_imported=value['profiles_imported'],
                conversation_selection_verified=current_selection,
                conversation_selection_sha256=current_selection_sha256,
                initial_conversation_selection_verified=value['conversation_selection_verified'],
                initial_retention_enabled=False,receipt_verified=True)


def seal_production_bootstrap(root, receipt_path, *, bundle_id, conversation_import,
                              observation_import, source_sha256, speaker_model_id,
                              single_writer_stopped=False):
    """Publish the private receipt LAST, after all five sources are imported.

    This does not perform a source snapshot/import or enable/start anything.
    Partial sealing is retryable only with the same bundle/source/import pins.
    """
    if single_writer_stopped is not True: _fail('single_writer_handoff_required')
    root = _private_root(root); receipt = Path(receipt_path).absolute()
    if receipt.parent!=root or receipt.exists() or re.fullmatch('[0-9a-f]{32}',bundle_id or '') is None:
        _fail('new_private_receipt_required')
    if set(source_sha256)!={'conversation','observation','speaker','anonymous_voice','identity_links'}:
        _fail('five_sources_required')
    for value in source_sha256.values(): _digest(value)
    imports = dict(conversation=conversation_import,observation=observation_import)
    for name,item in imports.items():
        if set(item)!={'import_id','source_sha256'} or item['source_sha256']!=source_sha256[name]:
            _fail('import_source_mismatch')
    manifest_hash = hashlib.sha256(_canonical(dict(sources=source_sha256,imports=imports)).encode()).hexdigest()
    targets,profile_count = {},None
    selection_verified,selection_sha256=False,None
    for kind,relative in TARGETS.items():
        path = _private_file(root,relative); db = _db(path,write=True)
        try:
            if db.execute('PRAGMA application_id').fetchone()[0]!=APPLICATION_IDS[kind]:
                _fail('target_application_mismatch')
            if kind == 'timeline':
                result = _import_marker(db,'bm_migrations',conversation_import)
                _import_marker(db,'bm_observation_migrations',observation_import)
                profile_count = result['profiles']
                if result['issued_profile_grants']!=0: _fail('unexpected_imported_grant')
                selection_verified,selection_sha256=_conversation_selection(root,db,initial=True,
                    import_id=conversation_import['import_id'])
                source_hash = hashlib.sha256(_canonical([source_sha256['conversation'],source_sha256['observation']]).encode()).hexdigest()
            else: source_hash = source_sha256[kind]
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(ORIGIN_TABLE,)).fetchone()
            if not exists:
                if kind!='timeline' and _hash(path)!=source_sha256[kind]:
                    _fail('speaker_target_not_exact_import_before_seal')
                db.execute(ORIGIN_DDL)
                db.execute('INSERT INTO bm_production_origin VALUES(1,?,?,?,?)',
                           (secrets.token_hex(16),bundle_id,source_hash,manifest_hash))
            origin = _read_origin(db)
            if (origin['bundle_id']!=bundle_id or origin['sources_sha256']!=source_hash or
                    origin['migration_manifest_sha256']!=manifest_hash):
                _fail('different_partial_migration_bundle')
            targets[kind] = dict(path=relative,database_uuid=origin['database_uuid'],sources_sha256=source_hash,
                migration_manifest_sha256=manifest_hash,schema_sha256=_schema_hash(db,kind),
                user_version=db.execute('PRAGMA user_version').fetchone()[0])
            db.commit()
        except BaseException:
            db.rollback(); raise
        finally: db.close()
    key = _private_file(root,'speaker/identity-link-receipt.key')
    if key.stat().st_size!=32: _fail('original_speaker_receipt_key_required')
    value = dict(schema=SCHEMA,bundle_id=bundle_id,data_origin='board',private_root=str(root),
                 initial_retention_enabled=False,targets=targets,imports=imports,
                 profiles_migration_verified=True,profiles_imported=profile_count,
                 conversation_selection_verified=selection_verified,conversation_selection_sha256=selection_sha256,
                 speaker_model_id=speaker_model_id,speaker_receipt_key_sha256=_hash(key))
    temporary = receipt.with_name(receipt.name+'.partial-'+secrets.token_hex(4))
    fd = os.open(str(temporary),os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write((_canonical(value)+'\n').encode()); stream.flush(); os.fsync(stream.fileno())
        # Verify the new private file and all immutable markers before publish.
        digest = _hash(temporary)
        verify_production_bootstrap(root,temporary,digest)
        if receipt.exists(): _fail('receipt_publish_conflict')
        os.replace(temporary,receipt)
    finally:
        if temporary.exists(): temporary.unlink()
    return dict(receipt_sha256=digest,bundle_id=bundle_id,initial_retention_enabled=False,
                profiles_imported=profile_count,target_paths=dict(TARGETS))
