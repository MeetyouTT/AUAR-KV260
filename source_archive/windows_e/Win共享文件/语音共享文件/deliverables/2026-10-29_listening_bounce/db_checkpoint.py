"""Independent WMI process: snapshot the actual production file view, metadata only."""
import argparse,datetime,hashlib,json,os,re,sqlite3
from pathlib import Path
H=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--job-id',required=True);parser.add_argument('--phase',choices=['before','after'],required=True)
args=parser.parse_args();assert re.fullmatch('[0-9a-f]{32}',args.job_id)
report={'pid':os.getpid(),'phase':args.phase,'launch_context':'independent_WMI_production_view',
        'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'databases':{}}
try:
    private=Path.home()/'AppData/Local/Aura/memory-upgrades'/('handoff-20261029-'+args.job_id+'-'+args.phase)
    private.mkdir(parents=True,exist_ok=False)
    for name,source in [('conversation',H.parent/'2026-10-18_board_dialogue/model_host/conversations.sqlite3'),
        ('observation',Path.home()/'AppData/Local/Aura/device-memory/observations.sqlite3'),
        ('speaker',Path.home()/'AppData/Local/Aura/device-memory/speakers.sqlite3')]:
        if not source.is_file():report['databases'][name]={'exists':False};continue
        target=private/source.name
        with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as db,sqlite3.connect(str(target)) as snapshot:
            db.backup(snapshot)
            assert snapshot.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            tables=[r[0] for r in snapshot.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            counts={t:snapshot.execute('SELECT count(*) FROM "'+t+'"').fetchone()[0] for t in tables}
        report['databases'][name]={'exists':True,'snapshot':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'bytes':target.stat().st_size,'counts':counts,'integrity':'ok'}
    assert report['databases']['conversation']['exists'] and report['databases']['observation']['exists']
    report['status']='PASS'
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/('db_checkpoint_'+args.job_id+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
