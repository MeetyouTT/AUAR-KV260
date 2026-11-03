"""Explain an exact live-cache delta without weakening archived-source checks."""
import datetime,hashlib,json,sqlite3
from pathlib import Path
H=Path(__file__).resolve().parent
report={'status':'STARTING','launch_context':'independent_WMI_production_view'}
try:
 baseline=json.loads((H/'baseline.json').read_text(encoding='utf-8'))
 verification=json.loads((H/'database_verification.json').read_text(encoding='utf-8'))
 assert verification['status']=='FAIL','Keep the original strict equality result'
 comparisons=verification['comparisons']
 assert comparisons['conversation']['original_source_rows_unchanged'] and comparisons['speaker']['original_source_rows_unchanged']
 changed=[name for name,value in comparisons['observation']['table_sha256'].items() if value['before']!=value['after']]
 assert changed==['observations'],changed
 endpoints=json.loads((H/'endpoints.json').read_text(encoding='utf-8'))
 retention=endpoints['services']['memory']['health']['observation_retention_seconds'];assert retention==86400
 before=baseline['database_before']['databases']['observation']['snapshot']
 after=verification['databases']['observation']['snapshot']
 with sqlite3.connect(Path(before).as_uri()+'?mode=ro',uri=True) as old,sqlite3.connect(Path(after).as_uri()+'?mode=ro',uri=True) as current:
  columns=[row[1] for row in old.execute('PRAGMA table_info(observations)')]
  assert columns==['id','boot','epoch','frame','received','summary']
  original={row[0]:row for row in old.execute('SELECT * FROM observations')}
  later={row[0]:row for row in current.execute('SELECT * FROM observations')}
 assert set(later).issubset(original)
 assert all(row==original[key] for key,row in later.items()),'A retained cache row changed'
 removed=[row for key,row in original.items() if key not in later];assert len(removed)==1
 captured=datetime.datetime.fromisoformat(verification['checked_utc']).timestamp()
 assert all(type(row[4]) in (int,float) and row[4]<captured-retention for row in removed),'Never waive a nonexpired removal'
 report.update(status='PASS',conversation_and_speaker_sources_unchanged=True,
  visual_archive_and_revision_tables_unchanged=True,all_retained_cache_rows_identical=True,
  cache_before=len(original),cache_after=len(later),removed_count=len(removed),retention_seconds=retention,
  removed_rows=[{'row_sha256':hashlib.sha256(json.dumps(row,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),
                'age_at_after_snapshot_seconds':round(captured-row[4],2)} for row in removed],
  archived_visual_event_count=verification['databases']['observation']['counts']['visual_timeline'],
  original_strict_report_retained='database_verification.json',automatic_original_cache_policy=True,
  manual_deletion_performed=False,old_snapshot_restored=False,private_backups_only=True)
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'cache_retention_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
