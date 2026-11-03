"""Fresh original-follow source closure and unchanged-owner assertions."""
import math

STARTUP_SHA='226b5a20f0089f5c534b1d540dd3605d805c17f7f1bd371a6ab5b3a4b287ad15'
EXPECTED_OWNERS={
    'camera':dict(pid=430894,birth_ticks=4011213,command_sha256='acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'),
    'supervisor':dict(pid=496785,birth_ticks=4302772,command_sha256='48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'),
    'gtk':dict(pid=496789,birth_ticks=4302880,command_sha256='5a76cc797f9879db5e24912bd7c85d0d5199d3240c15ce1ebfa1ff9a8a870123')}

def finite(value):
    return type(value) in (int,float) and math.isfinite(value)

def numeric(obj):
    if not isinstance(obj,dict):return {}
    return {k:v for k,v in obj.items() if type(v) is bool or finite(v)}

def fingerprint(pid):
    path=Path('/proc')/str(pid)
    return dict(pid=pid,birth_ticks=int((path/'stat').read_text().rsplit(')',1)[1].split()[19]),command_sha256=digest(path/'cmdline'))

def safe_state(value):
    h=value.get('handsfree_dialogue',{});p=value.get('manual_pan',{});r=p.get('readback') or {}
    return dict(page=value.get('ui_page'),listening_state=h.get('state'),listening_enabled=h.get('enabled'),
                microphone_open=h.get('microphone_open'),playing=value.get('playing'),pan_state=p.get('state'),
                following=p.get('automatic_following'),readback={k:r.get(k) for k in
                ('flags','width_us','lease_left_ms','active','armed','referenced','bound')},
                runtime_fault_count=value.get('runtime_faults',{}).get('count'))

def assert_safe(value):
    s=safe_state(value);r=s['readback']
    assert s['listening_state']=='PAUSED' and s['listening_enabled'] is False
    assert s['microphone_open'] is False and s['playing'] is False
    assert s['following'] is False and s['pan_state']=='READY'
    assert r['flags']==0 and r['lease_left_ms']==0 and r['active'] is False and r['armed'] is False
    return s

def preflight():
    current_guard();wide_active();verify_wide_files()
    assert digest(BUSINESS/'production_source_manifest.json')=='8ff79452570385921e06c098b5d42c2ea1ef5dfb84d81dfa7f53a9295373d0e8'
    startup=document(BUSINESS/'startup/config.json');pins=startup['component_sha256'];assert len(pins)==380
    assert all(digest(BUSINESS/'runtime/aura'/p)==h for p,h in pins.items())
    assert digest('/sys/firmware/fdt')=='aed6f0cbe5184a6eed38449731e92106b923573cb324fa4c68079fdb5bbfd53e'
    candidate,proof=verify_binding()
    assert len(candidate['source_sha256'])==23
    owners={k:fingerprint(v['pid']) for k,v in EXPECTED_OWNERS.items()};assert owners==EXPECTED_OWNERS
    for unit,role in [('aura-camera-ui.service','camera'),('aura-avatar-ui.service','supervisor')]:
        p=subprocess.run(['systemctl','show',unit,'--property=MainPID','--value'],capture_output=True,text=True,timeout=5)
        assert p.returncode==0 and int(p.stdout.strip())==owners[role]['pid']
    assert document(BUSINESS/'runtime/launch.json')['pid']==owners['gtk']['pid']
    manual=document(BUSINESS/'runtime/aura/config/pan_manual.local.json');face=document(manual['face_follow_config'])
    original=Path('/home/root/aura-pan-wide-20261028/control-10282601');assert Path(face['release_root'])==original
    assert digest(original/'deployment-manifest.json')==face['manifest_sha256']=='5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562'
    manifest=document(original/'deployment-manifest.json');assert len(manifest['files'])==25
    assert all(digest(row['destination'])==row['sha256'] for row in manifest['files'])
    assert document(face['arguments']['direction-evidence'])['axis_camera_mirrored_control_polarity']==1
    v=get_json(8783,'/api/state');h=get_json(8790,'/health');s=assert_safe(v)
    assert h['pid']==owners['camera']['pid'] and h['dpu_schedule']['owner_fenced'] is False
    assert h['camera_error']==h['detector_error']==h['identity']['error']==''
    return dict(observed_mono=time.monotonic(),boot_id=BOOT,startup_sha256=STARTUP_SHA,
                manifest_sha256='8ff79452570385921e06c098b5d42c2ea1ef5dfb84d81dfa7f53a9295373d0e8',
                configuration_sha256=digest(BUSINESS/'runtime/aura/config/board_avatar_gtk.json'),
                component_pins=380,all_component_bytes_match=True,camera_source_pins=23,
                original_controller_pins=25,original_controller_unchanged=True,owners=owners,
                firmware=firmware(),vart_exact_wide=True,fdt_sha256=digest('/sys/firmware/fdt'),
                state=s),v,h

def command_page(page):
    assert page in ('main','vision','settings')
    c=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
    try:
        c.request('POST','/api/command',body=json.dumps(dict(type='ui_page',page=page)),
                  headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
        r=c.getresponse();raw=r.read(100001);assert r.status==200 and len(raw)<=100000
        return json.loads(raw)
    finally:c.close()
