"""Select a real row through GTK and require a new accepted service receipt."""
import base64,hashlib,json,sys,time,urllib.error,urllib.request
from pathlib import Path
STAGE=Path('/home/root/aura-bytetrack-20261011/update-ea926df36eb116cd')
CONTEXT=STAGE.parent/'choice-3fbffdcd96534a3384ffab6c770e3e79.json'
manifest=json.loads((STAGE/'payload/manifest.json').read_text())
assert hashlib.sha256((STAGE/'payload/board_probe.py').read_bytes()).hexdigest()==manifest['files']['board_probe.py']['sha256']
sys.path.insert(0,str(STAGE/'payload'))
from board_probe import api,click,report


def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8790'+path,timeout=4) as stream:return json.load(stream)


def main():
    context=json.loads(CONTEXT.read_text());initial=api();health=get('/health')
    assert initial['ui_runtime']['ui_epoch']==context['before']['ui_runtime']['ui_epoch']
    assert initial['ui_runtime']['snapshot']['source_kind']=='actual'
    result={'scope':'REAL_NATIVE_TARGET_SELECTION','context_path':str(CONTEXT),'before':initial,
            'health_before':health,'artifacts':{},'observations':[]}
    baseline={row['command_id'] for row in initial['ui_runtime']['results']}
    _,geometry=report()
    dialogs=[row for row in geometry['ui_geometry']['dialogs'] if row.get('title')]
    if len(dialogs)!=1 or dialogs[0]['title']!='选择当前对象':
        result.update(status='PENDING_CHOOSER_NOT_OPEN',ui_after=api());return result
    dialog=dialogs[0]
    expected=context['before']['ui_runtime']['snapshot']['modules']['target']['tracks'][0]['key']
    ui=api();tracks=ui['ui_runtime']['snapshot']['modules']['target']['tracks']
    if not any(row['key']==expected for row in tracks):
        # A frozen chooser must not submit a target from an ended lifecycle.
        result['stale_chooser_key']=expected
        click(dialog['x']+dialog['width']*.81,dialog['y']+dialog['height']-41);time.sleep(.2)
        deadline=time.monotonic()+30;key=None;since=time.monotonic();stable=False
        while time.monotonic()<deadline:
            ui=api();snapshot=ui['ui_runtime']['snapshot']
            rows=snapshot['modules']['target']['tracks'] if snapshot else []
            current=rows[0]['key'] if rows and snapshot['capabilities']['target_select'] else None
            if current!=key:key=current;since=time.monotonic()
            if key and time.monotonic()-since>=1:stable=True;break
            time.sleep(.2)
        if not stable:
            result.update(status='PENDING_STABLE_REAL_PERSON',ui_after=api());return result
        expected=key
        # Device button and first row positions were verified in the real screen.
        click(98,442);time.sleep(.25)
        result['reopened_fresh_chooser']=True
    result['expected_target']=expected
    click(dialog['x']+dialog['width']/2,dialog['y']+72)
    result['native_row_clicked']=True
    deadline=time.monotonic()+7;receipt=None
    while time.monotonic()<deadline:
        ui=api()
        new=[row for row in ui['ui_runtime']['results'] if row['command_id'] not in baseline and row['action']=='target_select']
        if new:receipt=new[-1];break
        time.sleep(.12)
    result['receipt']=receipt
    if not receipt or not receipt.get('accepted'):
        result.update(status='REJECTED_OR_NOT_SUBMITTED',ui_after=ui);return result
    result['accepted_at']=get('/v1/ui/status')
    for _ in range(40):
        s=get('/v1/ui/status');h=get('/health')
        assert h['pid']==health['pid'] and h['service_epoch']==health['service_epoch']
        assert not any(h[k] for k in ('camera_error','detector_error','preview_error'))
        result['observations'].append({'observed_mono_ms':s['observed_mono_ms'],
            'target':s['modules']['target'],'people_count':s['modules']['vision'].get('people_count'),
            'detected_frames':h['detected_frames']})
        time.sleep(.12)
    result['selected_matches']=sum(row['target']['selected']==expected for row in result['observations'])
    result['health_after']=get('/health');result['ui_after']=api()
    result['status']='PASS_RECEIPT_AND_SELECTION' if result['selected_matches'] else 'RECEIPT_ACCEPTED_APPLY_UNVERIFIED'
    s=get('/v1/ui/status');ref=s.get('preview')
    if ref:
        try:
            with urllib.request.urlopen('http://127.0.0.1:8790/v1/ui/preview.jpg?camera_epoch='+ref['camera_epoch']+'&frame_id='+str(ref['frame_id']),timeout=4) as stream:
                assert stream.headers['X-Aura-Frame-Id']==str(ref['frame_id']);blob=stream.read()
            result['frame_reference']=ref
            result['artifacts']['after-selection.jpg']={'base64':base64.b64encode(blob).decode(),
                'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()}
        except urllib.error.HTTPError as exc:result['preview_fetch_error']=str(exc)
    for key in ('volume','muted','fullscreen','economy'):
        assert result['ui_after']['ui_settings'][key]==initial['ui_settings'][key],key
    assert api({'type':'ui_page','page':'main'})['ok']
    return result


print(json.dumps(main(),ensure_ascii=False))
