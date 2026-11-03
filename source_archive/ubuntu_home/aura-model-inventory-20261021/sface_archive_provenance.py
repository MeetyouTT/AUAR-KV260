import json,sqlite3
from collections import Counter
from pathlib import Path
p=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-slot-wait-81e6463c3747-298300/board_camera_ui.json')
c=json.loads(Path(json.loads(p.read_text())['identity']['config']).read_text());db=Path(c['database']).expanduser()
con=sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True)
revision=con.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0];con.close()
root=Path(c['enrollment_photos']['directory']).expanduser();rows=[]
for path in root.glob('*/manifest.json'):
 d=json.loads(path.read_text());rows.append({'outcome':d.get('outcome'),'schema':d.get('schema'),
 'revision_before':d.get('database_revision_before'),'revision_after':d.get('database_revision_after'),
 'images':len(d.get('images',[])),'decisions':dict(Counter(r.get('decision') for r in d.get('images',[]))),
 'selected':bool(d.get('selected')),'validation_frames':len(d.get('validation_frame_ids',[])),
 'template_policy':d.get('template_policy'),'truncated':d.get('truncated')})
print(json.dumps({'read_only':True,'database_revision':revision,'archives':rows}))
