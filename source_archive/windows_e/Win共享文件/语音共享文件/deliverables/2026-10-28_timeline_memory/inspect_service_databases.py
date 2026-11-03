"""Run through WMI like the production service to inspect its private file view."""
import argparse,datetime,hashlib,json,os,sqlite3,time,uuid
from pathlib import Path
H=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--backup',action='store_true');args=parser.parse_args()
report={'pid':os.getpid(),'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'launch_context':'independent_WMI_like_production','databases':{}}
try:
    for name,source in [('observation',Path.home()/'AppData/Local/Aura/device-memory/observations.sqlite3'),
                        ('conversation',H.parent/'2026-10-18_board_dialogue/model_host/conversations.sqlite3')]:
        with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as db:
            tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            counts={t:db.execute('SELECT count(*) FROM "'+t+'"').fetchone()[0] for t in tables}
            value={'path':str(source),'bytes':source.stat().st_size,'tables':tables,'counts':counts,
                   'integrity':db.execute('PRAGMA integrity_check').fetchone()[0]}
            if args.backup:
                directory=Path.home()/'AppData/Local/Aura/memory-upgrades'/('timeline-physical-after-'+uuid.uuid4().hex)
                directory.mkdir(parents=True);target=directory/source.name
                with sqlite3.connect(str(target)) as destination:db.backup(destination)
                value['post_upgrade_snapshot']=str(target);value['snapshot_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
            report['databases'][name]=value
    report['status']='PASS' if 'visual_timeline' in report['databases']['observation']['tables'] else 'SCHEMA_MISMATCH'
except Exception as exc:report.update(status='ERROR',error=type(exc).__name__+': '+str(exc))
(H/'physical_database_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
