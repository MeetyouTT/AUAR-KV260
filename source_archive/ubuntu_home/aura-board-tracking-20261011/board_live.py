"""One continuous native selection with actual camera data and an accepted receipt."""
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
    result={'scope':'REAL_NATIVE_TARGET_SELECTION','before':initial,'health_before':health,
            'artifacts':{},'observations':[]}
    _,geometry=report()
    dialogs=[row for row in geometry['ui_geometry']['dialogs'] if row.get('title')]
    if dialogs:
        result.update(status='PENDING_USER_DIALOG_OPEN',dialogs=dialogs,ui_after=api());return result
    assert api({'type':'ui_page','page':'devices'})['ok'];time.sleep(.3)
    # Native device-button and first-row positions were inspected in the actual
    # 1024x600 screenshot. The fixed-size chooser remains centred on the parent.
    _,geometry=report()
    assert (geometry['ui_geometry']['width'],geometry['ui_geometry']['height'])==(1024,600)
    rect=geometry['ui_geometry']['visible_controls']['target_select']
    result['button_geometry']=rect;result['chooser_geometry_reference']=context['dialog']
    key=None;since=time.monotonic();start=time.monotonic();deadline=start+30;stable=False
    while time.monotonic()<deadline:
        ui=api();snapshot=ui['ui_runtime']['snapshot']
        rows=snapshot['modules']['target']['tracks'] if snapshot and snapshot['source_kind']=='actual' else []
        current=rows[0]['key'] if rows and snapshot['capabilities']['target_select'] else None
        if current!=key:key=current;since=time.monotonic()
        if key and time.monotonic()-since>=1:stable=True;break
        time.sleep(.12)
    result['wait_seconds']=round(time.monotonic()-start,3)
    if not stable:
        result.update(status='PENDING_STABLE_REAL_PERSON',ui_after=api())
        assert api({'type':'ui_page','page':'main'})['ok']
        assert api({'type':'preview_open'})['ok'];return result
    result['expected_target']=key;baseline={row['command_id'] for row in ui['ui_runtime']['results']}
    result['ui_before_click']=ui
    click(rect['x']+rect['width']/2,rect['y']+rect['height']/2);time.sleep(.25)
    dialog=context['dialog']
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
        result.update(status='REJECTED_OR_NOT_SUBMITTED',ui_after=ui)
        return result
    result['accepted_at']=get('/v1/ui/status')
    for _ in range(40):
        s=get('/v1/ui/status');h=get('/health')
        assert h['pid']==health['pid'] and h['service_epoch']==health['service_epoch']
        assert not any(h[k] for k in ('camera_error','detector_error','preview_error'))
        result['observations'].append({'observed_mono_ms':s['observed_mono_ms'],
            'target':s['modules']['target'],'people_count':s['modules']['vision'].get('people_count'),
            'detected_frames':h['detected_frames']})
        time.sleep(.12)
    result['selected_matches']=sum(row['target']['selected']==key for row in result['observations'])
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
    for name in ('volume','muted','fullscreen','economy'):
        assert result['ui_after']['ui_settings'][name]==initial['ui_settings'][name],name
    _,closed=report()
    assert not [row for row in closed['ui_geometry']['dialogs'] if row.get('title')]
    result['closed_geometry']=closed['ui_geometry']
    assert api({'type':'ui_page','page':'main'})['ok']
    assert api({'type':'preview_open'})['ok']
    return result


print(json.dumps(main(),ensure_ascii=False))
