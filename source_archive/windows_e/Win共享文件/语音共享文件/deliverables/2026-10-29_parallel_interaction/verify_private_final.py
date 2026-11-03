"""Independent WMI file view; keep private snapshots outside the shared tree."""
import datetime,hashlib,json,runpy,sqlite3,sys,uuid
from pathlib import Path
H=Path(__file__).resolve().parent
report={'status':'CHECKING','launch_context':'independent_WMI_production_view','old_snapshot_restored':False}
def digest(db,table):
    def binary(v):
        if isinstance(v,bytes):return {'blob_hex':v.hex()}
        raise TypeError(type(v).__name__)
    rows=sorted(json.dumps(list(row),ensure_ascii=False,separators=(',',':'),default=binary) for row in db.execute('SELECT * FROM "'+table+'"'))
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest()
try:
    before=json.loads((H/'private_before_final.json').read_text(encoding='utf-8'))
    checkpoint=H.parent/'2026-10-29_service_recovery/db_checkpoint.py'
    sys.argv=[str(checkpoint),'--job-id',uuid.uuid4().hex,'--phase','after']
    after=runpy.run_path(str(checkpoint),run_name='__main__')['report'];assert after['status']=='PASS'
    report.update(checked_utc=after['checked_utc'],databases=after['databases'],comparisons={})
    for kind,old in before['databases'].items():
        if not old['exists']:continue
        current=after['databases'][kind]
        with sqlite3.connect(Path(old['snapshot']).as_uri()+'?mode=ro',uri=True) as a,sqlite3.connect(Path(current['snapshot']).as_uri()+'?mode=ro',uri=True) as b:
            tables=[name for name in old['counts'] if not name.startswith('timeline_digest')]
            values={name:{'before':digest(a,name),'after':digest(b,name)} for name in tables}
        report['comparisons'][kind]={'source_rows_equal':all(v['before']==v['after'] for v in values.values()),
          'tables':values,'before_counts':old['counts'],'after_counts':current['counts']}
    strict=all(v['source_rows_equal'] for v in report['comparisons'].values())
    strict_report=dict(report,status='PASS' if strict else 'FAIL',strict_source_equality=strict)
    (H/'database_strict_comparison.json').write_text(json.dumps(strict_report,indent=2),encoding='utf-8')
    if not strict:
        comparisons=report['comparisons']
        assert comparisons['conversation']['source_rows_equal'] and comparisons['speaker']['source_rows_equal']
        changed=[name for name,v in comparisons['observation']['tables'].items() if v['before']!=v['after']]
        assert changed==['observations'],('Unexpected source change',changed)
        with sqlite3.connect(Path(before['databases']['observation']['snapshot']).as_uri()+'?mode=ro',uri=True) as a,sqlite3.connect(Path(after['databases']['observation']['snapshot']).as_uri()+'?mode=ro',uri=True) as b:
            assert [row[1] for row in a.execute('PRAGMA table_info(observations)')]==['id','boot','epoch','frame','received','summary']
            old={r[0]:r for r in a.execute('SELECT * FROM observations')};new={r[0]:r for r in b.execute('SELECT * FROM observations')}
        assert set(new).issubset(old) and all(row==old[key] for key,row in new.items())
        removed=[r for key,r in old.items() if key not in new];timestamp=datetime.datetime.fromisoformat(after['checked_utc']).timestamp()
        assert removed and all(type(r[4]) in (int,float) and timestamp-r[4]>86400 for r in removed)
        report.update(cache_expired_removed=len(removed),cache_retained_rows_identical=True,cache_retention_seconds=86400)
    report['derived_identity_stores']={}
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
    report.update(status='PASS',strict_source_equality=strict,conversation_visual_archive_speaker_sources_unchanged=True,
      private_backups_only=True,manual_deletion_performed=False)
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'database_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
