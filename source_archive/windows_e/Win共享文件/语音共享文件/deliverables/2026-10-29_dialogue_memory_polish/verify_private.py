"""Run through independent WMI; compare original source rows without exporting them."""
import hashlib,json,runpy,sqlite3,sys,uuid
from pathlib import Path
H=Path(__file__).resolve().parent
out=H/'physical_database_check.json'
report={'status':'STARTING','launch_context':'independent_WMI_production_view'}
def digest(db,table):
    def binary(value):
        if isinstance(value,bytes):return {'blob_hex':value.hex()}
        raise TypeError(type(value).__name__)
    rows=[json.dumps(list(r),ensure_ascii=False,separators=(',',':'),default=binary) for r in db.execute('SELECT * FROM "'+table+'"')]
    rows.sort()
    return hashlib.sha256('\n'.join(rows).encode()).hexdigest()
try:
    deployment=json.loads((H/'deployment.json').read_text(encoding='utf-8'))
    assert deployment['status']=='COMMITTED'
    sys.argv=[str(H/'db_checkpoint.py'),'--job-id',uuid.uuid4().hex,'--phase','after']
    after=runpy.run_path(str(H/'db_checkpoint.py'),run_name='__main__')['report']
    assert after['status']=='PASS'
    report.update(checked_utc=after['checked_utc'],databases=after['databases'],comparisons={})
    original=json.loads((H/'original_database_checkpoint.json').read_text(encoding='utf-8'))
    for kind,previous in original['databases'].items():
        if not previous['exists']:continue
        current=after['databases'][kind]
        with sqlite3.connect(Path(previous['snapshot']).as_uri()+'?mode=ro',uri=True) as before_db,sqlite3.connect(Path(current['snapshot']).as_uri()+'?mode=ro',uri=True) as after_db:
            tables=['observations','visual_timeline'] if kind=='observation' else [t for t in previous['counts'] if not t.startswith('timeline_digest')]
            results={t:{'before':digest(before_db,t),'after':digest(after_db,t)} for t in tables}
        assert all(v['before']==v['after'] for v in results.values()),'Pre-existing source data changed: '+kind
        report['comparisons'][kind]={'source_rows_unchanged':True,'table_sha256':results}
    assert after['databases']['conversation']['counts']['timeline_digests']>0
    assert after['databases']['observation']['counts']['timeline_digests']>0
    report.update(status='PASS',original_sources_unchanged=True,private_backups_only=True)
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
