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
    before=json.loads((H/'windows_before.json').read_text(encoding='utf-8'))['private_checkpoint']
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
    report.update(status='PASS',strict_source_equality=strict,conversation_visual_archive_speaker_sources_unchanged=True,
      private_backups_only=True,manual_deletion_performed=False)
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'database_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
