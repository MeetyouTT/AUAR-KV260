"""Run in an independent WMI process; only hashes/counts leave private storage."""
import hashlib,json,sqlite3
from pathlib import Path
H=Path(__file__).resolve().parent
def read(name):return json.loads((H/name).read_text(encoding='utf-8-sig'))
def digest(db,table):
    def binary(value):
        if isinstance(value,bytes):return {'blob_hex':value.hex()}
        raise TypeError(type(value).__name__)
    values=sorted(json.dumps(list(row),ensure_ascii=False,separators=(',',':'),default=binary) for row in db.execute('SELECT * FROM "'+table+'"'))
    return hashlib.sha256('\n'.join(values).encode()).hexdigest()
report={'status':'CHECKING','old_snapshot_restored':False,'private_backups_only':True,'comparisons':{}}
try:
    before=read('baseline.json')['private_checkpoint'];after=read('private_after.json')
    for kind,old in before['databases'].items():
        if not old['exists']:continue
        new=after['databases'][kind]
        with sqlite3.connect(Path(old['snapshot']).as_uri()+'?mode=ro',uri=True) as a,sqlite3.connect(Path(new['snapshot']).as_uri()+'?mode=ro',uri=True) as b:
            tables=[t for t in old['counts'] if not t.startswith('timeline_digest')]
            values={t:{'before':digest(a,t),'after':digest(b,t)} for t in tables}
            changed=[t for t,v in values.items() if v['before']!=v['after']]
            if kind=='observation' and changed==['observations']:
                previous={r[0]:r for r in a.execute('SELECT * FROM observations')};current={r[0]:r for r in b.execute('SELECT * FROM observations')}
                assert set(current)<=set(previous) and all(r==previous[k] for k,r in current.items())
                import datetime
                at=datetime.datetime.fromisoformat(after['checked_utc']).timestamp()
                removed=[r for k,r in previous.items() if k not in current]
                assert removed and all(at-r[4]>86400 for r in removed)
                report['expired_live_cache_rows']=len(removed)
            else:assert not changed,(kind,changed)
        report['comparisons'][kind]={'source_rows_equal':not changed,'tables':values,'before_counts':old['counts'],'after_counts':new['counts']}
    report['derived_integrity']={}
    private=Path.home()/'AppData/Local/Aura/device-memory'
    for name in ('anonymous-voices.sqlite3','identity-links.sqlite3'):
        with sqlite3.connect((private/name).as_uri()+'?mode=ro',uri=True) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            report['derived_integrity'][name]={'integrity':'ok','counts':{t:db.execute('SELECT count(*) FROM "'+t+'"').fetchone()[0] for t in tables}}
    report['status']='PASS'
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'database_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
