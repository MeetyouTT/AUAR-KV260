"""Observe loss and return of the actual manually selected lifecycle."""
import base64,hashlib,json,time,urllib.error,urllib.request
expected={'camera_epoch':'7134c8a136ab47aeb50e9b0205061105','track_id':97,'track_generation':2}


def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8790'+path,timeout=4) as stream:return json.load(stream)


before=get('/health');assert before['camera_epoch']==expected['camera_epoch']
result={'scope':'REAL_MANUAL_TARGET_LOSS_AND_RETURN','expected_target':expected,'before':before,
        'observations':[],'artifacts':{}}
start=time.monotonic();deadline=start+45;lost=False;returned=False
while time.monotonic()<deadline:
    s=get('/v1/ui/status');h=get('/health');target=s['modules']['target']
    assert s['source_kind']=='actual' and h['service_epoch']==before['service_epoch'] and h['pid']==before['pid']
    assert not any(h[k] for k in ('camera_error','detector_error','preview_error'))
    visible=any(row['key']==expected for row in target['tracks'])
    if not visible:
        assert target['selected'] is None,'Manual binding transferred after loss'
        lost=True
    if lost and target['tracks'] and not visible:
        assert target['selected'] is None;returned=True
    result['observations'].append({'elapsed_s':round(time.monotonic()-start,3),
        'observed_mono_ms':s['observed_mono_ms'],'target':target,
        'people_count':s['modules']['vision'].get('people_count'),'detected_frames':h['detected_frames']})
    time.sleep(.2)
result.update(observation_seconds=round(time.monotonic()-start,3),lost_observed=lost,
              new_lifecycle_observed_without_selection=returned,after=get('/health'))
result['status']='PASS_LOSS_AND_NEW_LIFECYCLE' if returned else 'PASS_LOSS_RETURN_PENDING' if lost else 'PENDING_PHYSICAL_LOSS'
s=get('/v1/ui/status');ref=s.get('preview');result['last_snapshot']=s
if ref:
    try:
        with urllib.request.urlopen('http://127.0.0.1:8790/v1/ui/preview.jpg?camera_epoch='+ref['camera_epoch']+'&frame_id='+str(ref['frame_id']),timeout=4) as stream:
            assert stream.headers['X-Aura-Frame-Id']==str(ref['frame_id']);blob=stream.read()
        result['frame_reference']=ref
        result['artifacts']['after-return.jpg']={'base64':base64.b64encode(blob).decode(),
            'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()}
    except urllib.error.HTTPError as exc:result['preview_fetch_error']=str(exc)
print(json.dumps(result,ensure_ascii=False))
