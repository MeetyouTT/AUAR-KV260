"""Run under hidden WMI; compare original source rows using private snapshots."""
import datetime,hashlib,json,runpy,sqlite3,sys,uuid
from pathlib import Path
H=Path(__file__).resolve().parent
report={'status':'STARTING','launch_context':'independent_WMI_production_view'}
def digest(db,table):
 def binary(value):
  if isinstance(value,bytes):return {'blob_hex':value.hex()}
  raise TypeError(type(value).__name__)
 rows=sorted(json.dumps(list(row),ensure_ascii=False,separators=(',',':'),default=binary) for row in db.execute('SELECT * FROM "'+table+'"'))
 return hashlib.sha256('\n'.join(rows).encode()).hexdigest()
try:
 before=json.loads((H/'baseline.json').read_text(encoding='utf-8'))['database_before']
 sys.argv=[str(H/'db_checkpoint.py'),'--job-id',uuid.uuid4().hex,'--phase','after']
 after=runpy.run_path(str(H/'db_checkpoint.py'),run_name='__main__')['report'];assert after['status']=='PASS'
 report.update(checked_utc=after['checked_utc'],databases=after['databases'],comparisons={})
 for kind,old in before['databases'].items():
  if not old['exists']:continue
  current=after['databases'][kind]
  with sqlite3.connect(Path(old['snapshot']).as_uri()+'?mode=ro',uri=True) as old_db,sqlite3.connect(Path(current['snapshot']).as_uri()+'?mode=ro',uri=True) as current_db:
   tables=[name for name in old['counts'] if not name.startswith('timeline_digest')]
   compared={name:{'before':digest(old_db,name),'after':digest(current_db,name)} for name in tables}
  unchanged=all(v['before']==v['after'] for v in compared.values())
  report['comparisons'][kind]={'original_source_rows_unchanged':unchanged,'table_sha256':compared,
   'before_counts':old['counts'],'after_counts':current['counts']}
 assert all(value['original_source_rows_unchanged'] for value in report['comparisons'].values()),'Inspect source changes; never restore older data automatically'
 report.update(status='PASS',original_sources_unchanged=True,private_backups_only=True)
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'database_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
