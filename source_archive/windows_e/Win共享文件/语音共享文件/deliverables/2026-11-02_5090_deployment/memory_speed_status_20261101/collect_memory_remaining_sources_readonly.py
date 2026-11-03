import datetime,json,sqlite3,time
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='903cfade-b93c-48fa-804e-379be1967313'
p=Path('/home/root/.local/share/aura-board-business/timeline.sqlite3');before=p.stat();assert p.resolve()==p and not p.is_symlink()
db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=2,isolation_level=None)
try:
 db.execute('PRAGMA query_only=ON');assert db.execute('PRAGMA query_only').fetchone()==(1,)
 db.execute('BEGIN')
 counts={}
 for source in ('user_said','assistant_reply','assistant_played','camera_observed','device_event','memory_command'):
  counts[source]=db.execute("SELECT COUNT(*) FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.state='valid' AND e.compacted_summary_id IS NULL AND e.source=?",(source,)).fetchone()[0]
 scope_counts={scope:db.execute('SELECT COUNT(*) FROM bm_turns WHERE scope_kind=?',(scope,)).fetchone()[0] for scope in ('conversation','profile','device')}
 oldest=db.execute("SELECT MIN(e.recorded_utc) FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.state='valid' AND e.compacted_summary_id IS NULL").fetchone()[0]
 total=db.execute("SELECT COUNT(*) FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.state='valid' AND e.compacted_summary_id IS NULL").fetchone()[0]
 counts['other']=total-sum(counts.values())
 db.execute('ROLLBACK')
finally:db.close()
after=p.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pending_valid_body_sources':counts,'turn_scope_counts':scope_counts,'oldest_pending_body_recorded_utc':datetime.datetime.fromtimestamp(oldest,datetime.timezone.utc).isoformat() if oldest else None,'read_only':True,'raw_text_or_ids_exported':False}))
