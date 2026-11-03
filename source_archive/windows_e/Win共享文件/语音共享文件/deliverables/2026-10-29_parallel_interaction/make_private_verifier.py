from pathlib import Path
H=Path(__file__).resolve().parent
s=(H.parent/'2026-10-29_audio_animation_polish/verify_private_data.py').read_text(encoding='utf-8')
old="before=json.loads((H/'windows_before.json').read_text(encoding='utf-8'))['private_checkpoint']"
assert s.count(old)==1;s=s.replace(old,"before=json.loads((H/'private_before_final.json').read_text(encoding='utf-8'))")
needle="    report.update(status='PASS',strict_source_equality=strict,conversation_visual_archive_speaker_sources_unchanged=True,"
assert s.count(needle)==1
s=s.replace(needle,'''    report['derived_identity_stores']={}
    private_root=Path.home()/'AppData/Local/Aura/device-memory'
    snapshot_root=Path(after['databases']['speaker']['snapshot']).parent
    for filename in ('anonymous-voices.sqlite3','identity-links.sqlite3'):
        source=private_root/filename;target=snapshot_root/filename
        with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as db,sqlite3.connect(str(target)) as saved:
            db.backup(saved);assert saved.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            tables=[r[0] for r in saved.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            counts={name:saved.execute('SELECT count(*) FROM "'+name+'"').fetchone()[0] for name in tables}
        report['derived_identity_stores'][filename]={'snapshot':str(target),'counts':counts,
            'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'integrity':'ok','private_backup_only':True}
    report.update(status='PASS',strict_source_equality=strict,conversation_visual_archive_speaker_sources_unchanged=True,''')
compile(s,'verify_private_final.py','exec');(H/'verify_private_final.py').write_text(s,encoding='utf-8')
print('Independent private verifier prepared')
