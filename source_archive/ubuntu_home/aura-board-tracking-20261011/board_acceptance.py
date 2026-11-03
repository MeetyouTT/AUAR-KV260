"""Real-camera target selection through the native GUI; no synthetic feed."""
import base64,hashlib,json,time,urllib.request
from board_probe import api,click,report

def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8790'+path,timeout=4) as stream:return json.load(stream)

end=time.monotonic()+20
snapshot=None
while time.monotonic()<end:
    snapshot=get('/v1/ui/status')
    if snapshot['modules']['target']['tracks']:break
    time.sleep(.2)
tracks=snapshot['modules']['target']['tracks']
result={'scope':'REAL_CAMERA_TARGET_SELECTION','positive_observed':bool(tracks)}
if tracks:
    assert api({'type':'ui_page','page':'devices'})['ok'];time.sleep(.4)
    _,geometry=report()
    rect=geometry['ui_geometry']['visible_controls']['target_select']
    assert rect['sensitive']
    click(rect['x']+rect['width']/2,rect['y']+rect['height']/2);time.sleep(.4)
    _,opened=report()
    dialog=opened['ui_geometry']['dialogs'][0]
    assert dialog['title']=='选择当前对象'
    # Undecorated dialog content starts with the scrolled target buttons.
    click(dialog['x']+dialog['width']/2,dialog['y']+40);time.sleep(.8)
    _,closed=report()
    if closed['ui_geometry']['dialogs']:
        click(dialog['x']+dialog['width']/2,dialog['y']+72);time.sleep(.6)
        _,closed=report()
    assert not closed['ui_geometry']['dialogs'],'Target chooser did not close'
    selected=get('/v1/ui/status')
    result['native_target_chooser']=True
    result['selected_snapshot']=selected
    assert selected['modules']['target']['selected'],selected
    assert not api()['error']
    ref=selected.get('preview')
    if ref:
        with urllib.request.urlopen('http://127.0.0.1:8790/v1/ui/preview.jpg?camera_epoch='+ref['camera_epoch']+'&frame_id='+str(ref['frame_id']),timeout=3) as stream:
            assert stream.headers['X-Aura-Frame-Id']==str(ref['frame_id'])
            blob=stream.read()
        result['artifacts']={'real-track.jpg':{'base64':base64.b64encode(blob).decode(),'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()}}
        result['frame_reference']=ref
    # Read-only stability window after the actual user-facing selection.
    observations=[]
    for _ in range(40):
        s=get('/v1/ui/status');h=get('/health')
        assert not h['camera_error'] and not h['detector_error'] and not h['preview_error']
        observations.append({'selected':s['modules']['target']['selected'],'tracks':s['modules']['target']['tracks'],
            'people_count':s['modules']['vision'].get('people_count'),'detected_frames':h['detected_frames'],
            'last_inference_ms':h['last_inference_ms']})
        time.sleep(.12)
    result['observations']=observations
    result['selection_matches_samples']=sum(r['selected']==selected['modules']['target']['selected'] for r in observations)
assert api({'type':'ui_page','page':'main'})['ok']
result['status']='PASS'
print(json.dumps(result,ensure_ascii=False))
