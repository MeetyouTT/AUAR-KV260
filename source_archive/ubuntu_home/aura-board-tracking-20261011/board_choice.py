"""Open the real target chooser and preserve its screen and command baseline."""
import base64, hashlib, json, sys, time, uuid
from pathlib import Path
STAGE=Path('/home/root/aura-bytetrack-20261011/update-ea926df36eb116cd')
manifest=json.loads((STAGE/'payload/manifest.json').read_text())
assert hashlib.sha256((STAGE/'payload/board_probe.py').read_bytes()).hexdigest()==manifest['files']['board_probe.py']['sha256']
sys.path.insert(0,str(STAGE/'payload'))
from board_probe import api,click,report,screenshot

before=api()
assert api({'type':'ui_page','page':'devices'})['ok'];time.sleep(.4)
_,data=report()
assert not [row for row in data['ui_geometry']['dialogs'] if row.get('title')]
rect=data['ui_geometry']['visible_controls']['target_select']
end=time.monotonic()+30
key=None;stable_since=time.monotonic();stable=False
while time.monotonic()<end:
    before=api()
    s=before['ui_runtime']['snapshot']
    tracks=s['modules']['target']['tracks'] if s and s['source_kind']=='actual' else []
    current=tracks[0]['key'] if tracks and s['capabilities'].get('target_select') else None
    if current!=key:key=current;stable_since=time.monotonic()
    if key and time.monotonic()-stable_since>=1:stable=True;break
    time.sleep(.2)
if not stable:
    print(json.dumps({'status':'PENDING_STABLE_REAL_PERSON','ui':before},ensure_ascii=False))
else:
    click(rect['x']+rect['width']/2,rect['y']+rect['height']/2);time.sleep(.4)
    _,opened=report()
    dialogs=[row for row in opened['ui_geometry']['dialogs'] if row.get('title')]
    if not dialogs:
        print(json.dumps({'status':'PENDING_PERSON_CHANGED_BEFORE_CHOOSER','ui':api()},ensure_ascii=False))
    else:
        dialog=dialogs[0];assert dialog['title']=='选择当前对象'
        shot=screenshot(opened,True)
        blob=base64.b64decode(shot.pop('jpeg_base64'),validate=True)
        context={'status':'CHOOSER_OPEN','before':before,'dialog':dialog,'ui_opened':api(),
                 'screenshot':shot,'geometry':opened['ui_geometry'],'errors':opened['errors'],
                 'input_events':opened['input_events'][-20:]}
        path=STAGE.parent/('choice-'+uuid.uuid4().hex+'.json')
        with path.open('x') as stream:json.dump(context,stream,ensure_ascii=False)
        context['context_path']=str(path)
        context['artifacts']={'target-chooser.jpg':{'base64':base64.b64encode(blob).decode(),
            'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()}}
        print(json.dumps(context,ensure_ascii=False))
