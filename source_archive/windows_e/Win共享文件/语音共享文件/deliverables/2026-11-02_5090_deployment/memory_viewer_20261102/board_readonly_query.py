"""Executed over verified SSH. Read-only, paginated, no application imports."""
import datetime
import json
from pathlib import Path
import sqlite3
import time

# The host prepends REQUEST as a JSON-decoded literal on stdin.
assert isinstance(REQUEST, dict)
kind = REQUEST.get('kind', 'conversation')
assert kind in ('all', 'conversation', 'vision', 'device', 'facts', 'recent')
page = REQUEST.get('page', 0)
query = REQUEST.get('query', '')
assert type(page) is int and 0 <= page <= 10000
assert type(query) is str and len(query) <= 100
path = Path('/home/root/.local/share/aura-board-business/timeline.sqlite3')
assert path.is_file() and not path.is_symlink() and path.resolve() == path
assert path.stat().st_size <= 128 * 1024 * 1024
db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, isolation_level=None, timeout=1)
db.row_factory = sqlite3.Row
deadline = time.monotonic() + 3
db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
try:
    db.execute('PRAGMA query_only=ON')
    assert db.execute('PRAGMA query_only').fetchone()[0] == 1
    assert db.execute('PRAGMA application_id').fetchone()[0] == 0x41555242
    assert db.execute("SELECT value FROM bm_meta WHERE key='schema_version'").fetchone()[0] == '1'
    assert db.execute("SELECT value FROM bm_meta WHERE key='data_origin'").fetchone()[0] == 'board'
    db.execute('BEGIN')
    counts = {key: db.execute(sql).fetchone()[0] for key, sql in {
        'summaries': "SELECT COUNT(*) FROM bm_summaries WHERE state='valid' AND scope_kind IN ('conversation','device')",
        'conversations': "SELECT COUNT(*) FROM bm_turns WHERE scope_kind='conversation'",
        'facts': "SELECT COUNT(*) FROM bm_facts WHERE state='current' AND scope_kind IN ('conversation','device')",
        'profiles': 'SELECT COUNT(*) FROM bm_profiles',
        'recent': "SELECT COUNT(*) FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.state='valid' AND e.scope_kind IN ('conversation','device')",
    }.items()}
    params = []
    search = '%' + query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
    if kind == 'facts':
        base = "FROM bm_facts WHERE state='current' AND scope_kind IN ('conversation','device')"
        if query:
            base += " AND (value LIKE ? ESCAPE '\\' OR fact_key LIKE ? ESCAPE '\\')"
            params += [search, search]
        fields = 'fact_key AS label, value AS text, created_utc AS start, created_utc AS end'
        order = 'created_utc DESC'
    elif kind == 'recent':
        base = "FROM bm_events e JOIN bm_bodies b USING(event_id) WHERE e.state='valid' AND e.scope_kind IN ('conversation','device')"
        if query:
            base += " AND b.text LIKE ? ESCAPE '\\'"
            params += [search]
        fields = 'e.source AS label,b.text AS text,e.recorded_utc AS start,e.recorded_utc AS end'
        order = 'e.recorded_utc DESC'
    else:
        base = "FROM bm_summaries s WHERE s.state='valid' AND s.scope_kind IN ('conversation','device')"
        source_groups = {
            'conversation': ('user_said','assistant_played','assistant_reply'),
            'vision': ('camera_observed',), 'device': ('device_event',)}
        if kind in source_groups:
            sources = source_groups[kind]
            marks = ','.join('?' for _ in sources)
            base += ' AND EXISTS (SELECT 1 FROM bm_summary_sources ss JOIN bm_events e USING(event_id) WHERE ss.summary_id=s.summary_id AND e.source IN (' + marks + '))'
            params += list(sources)
        if query:
            base += " AND (s.summary LIKE ? ESCAPE '\\' OR s.keywords LIKE ? ESCAPE '\\')"
            params += [search, search]
        fields = 's.topic AS label,s.summary AS text,s.keywords,s.start_utc AS start,s.end_utc AS end'
        order = 's.end_utc DESC,s.created_utc DESC,s.summary_id DESC'
    total = db.execute('SELECT COUNT(*) ' + base, params).fetchone()[0]
    rows = db.execute('SELECT ' + fields + ' ' + base + ' ORDER BY ' + order + ' LIMIT 20 OFFSET ?', params + [page * 20]).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        for key in ('start','end'):
            item[key] = datetime.datetime.fromtimestamp(item[key],datetime.timezone.utc).isoformat() if item[key] is not None else None
        for key in ('label','text','keywords'):
            if key in item:
                item[key] = str(item[key] or '')[:16384]
        items.append(item)
    db.execute('ROLLBACK')
finally:
    db.close()
print(json.dumps({'counts':counts,'total':total,'page':page,'page_size':20,'items':items,
    'read_only':True,'profile_content_included':False,
    'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},ensure_ascii=True))
