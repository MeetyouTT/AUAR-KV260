import json,sqlite3,sys,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent
report={'python':sys.executable,'home':str(Path.home()),'databases':{}}
for name,p in [('actual_user',Path(r'C:\Users\35870\AppData\Local\Aura\device-memory\observations.sqlite3')),
               ('python_home',Path.home()/'AppData/Local/Aura/device-memory/observations.sqlite3')]:
    with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
        tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        report['databases'][name]={'path':str(p),'bytes':p.stat().st_size,'tables':tables,
                                  'connection_path':db.execute('PRAGMA database_list').fetchall()}
request=urllib.request.Request('http://127.0.0.1:8812/v1/memory/timeline',
    data=json.dumps({'boot':'read-only-check','text':'昨天看到了什么'}).encode(),headers={'Content-Type':'application/json'})
with urllib.request.urlopen(request,timeout=3) as response:
    value=json.load(response);report['service']={'version':value.get('version'),'revision':value.get('revision'),'events':len(value.get('events',[]))}
(H/('database_locations_'+Path(sys.executable).parent.name+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
