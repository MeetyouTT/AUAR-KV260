"""Wire the reviewed freshness observer into the pinned 1ms-only trial."""
import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
HELPERS=Path('/home/ghmd/aura-identity-dpu-check-20261018')
base=HELPERS/'board_gil_switch_1ms_20261022.py'
assert hashlib.sha256(base.read_bytes()).hexdigest()=='cd64535922ae87f278913c3c43dec344dcb8d14bccfa29bde537145911402316'
candidate=Path('/home/ghmd/aura-freshness-light-20261022/candidate/aura')
files={name:(candidate/name).read_bytes() for name in
    ('board/identity/face_targets.py','board/identity/face_freshness_metrics.py')}
hashes={name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
assert hashes['board/identity/face_targets.py']=='2f68d7ae75f67b2b1c67e7513296d6a6e907e02bcc0a5867d0f09c8fd1075577'
assert hashes['board/identity/face_freshness_metrics.py']=='206f565044a94a7f3f8369d25a1f98e587107b5f025d16f3c2cab6c19fe4a160'
source=base.read_text().replace('215c4292-ce84-4828-9827-83c32ba66564','7924ac9f-311d-4fcd-98be-57bf023cf1aa')
source=source.replace("(usb/'devnum').read_text().strip()=='4'", "(usb/'devnum').read_text().strip()=='3'")
parsed=ast.parse(source)
constants={n.targets[0].id:ast.literal_eval(n.value) for n in parsed.body if isinstance(n,ast.Assign)
    and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('WRAPPER_B64','WRAPPER_SHA')}
wrapper=base64.b64decode(constants['WRAPPER_B64']).decode()
assert wrapper.count('/home/root/aura-dpu-vision-20261021/gil-switch-live')==1
wrapper=wrapper.replace('/home/root/aura-dpu-vision-20261021/gil-switch-live',
    '/home/root/aura-dpu-vision-20261021/postpower-metrics-live')
source=source.replace('WRAPPER_B64='+repr(constants['WRAPPER_B64']),
    'WRAPPER_B64='+repr(base64.b64encode(wrapper.encode()).decode()))
source=source.replace('WRAPPER_SHA='+repr(constants['WRAPPER_SHA']),
    'WRAPPER_SHA='+repr(hashlib.sha256(wrapper.encode()).hexdigest()))
source=source.replace('/gil-switch-live','/postpower-metrics-live').replace('gil-switch-launches','postpower-metrics-launches')
source=source.replace('aura-gil-switch-live-','aura-postpower-metrics-').replace('AURA_RUN_GIL_SWITCH_LIVE','AURA_RUN_POSTPOWER_METRICS')
source=source.replace('GIL_1MS_DUAL_MODEL_120S_ALWAYS_RESTORED','FRESHNESS_1MS_DUAL_MODEL_120S_ALWAYS_RESTORED')
source=source.replace('GIL_1MS_SHORT_WINDOW_ONLY_NOT_ROOT_CAUSE_OR_LONG_STABILITY_PROOF',
    'FRESHNESS_1MS_120S_DIAGNOSTIC_NOT_RETRY_OR_SPEEDUP_PROOF')
def replace(old,new):
    global source
    assert source.count(old)==1,(old[:100],source.count(old))
    source=source.replace(old,new)
replace("    path=candidate/'board/vision/ui_camera_service.py'", '''
    import gzip
    for name,encoded in FRESHNESS_PAYLOAD.items():
        data=gzip.decompress(base64.b64decode(encoded));assert hashlib.sha256(data).hexdigest()==FRESHNESS_HASHES[name]
        target=candidate/name;assert not target.is_symlink();target.write_bytes(data)
    face_source=candidate/'board/identity/camera_faces.py'
    text=face_source.read_text()
    old="minimum_score=config['minimum_face_score'],minimum_pixels=config['minimum_face_pixels'])"
    new="minimum_score=config['minimum_face_score'],minimum_pixels=config['minimum_face_pixels'],freshness_metrics=True)"
    assert text.count(old)==1;text=text.replace(old,new);ast.parse(text);face_source.write_text(text)
    path=candidate/'board/vision/ui_camera_service.py'
''')
replace("shadow=(identity.get('feature_inference') or {}).get('shadow'))",
        "shadow=(identity.get('feature_inference') or {}).get('shadow'))")
replace("'native_sources_unchanged_from_5ms_observer':True", "'native_sources_unchanged_from_5ms_observer':True,\n        'freshness_observer_hashes':FRESHNESS_HASHES,'freshness_wiring_sha256':digest(face_source)")
replace("            assert not observer['disabled_after_slow_read'],'Observer stopped after slow read'", '''
            assert not observer['disabled_after_slow_read'],'Observer stopped after slow read'
            freshness=state['face_targets']['freshness_metrics']
            assert freshness['enabled'] and freshness['collecting'] and not freshness['observer_failures']
            assert freshness['schema_version']=='aura-face-freshness-metrics-1'
''')
replace("        report['passed']=True;report['observation_status']='FRESHNESS_1MS_120S_DIAGNOSTIC_NOT_RETRY_OR_SPEEDUP_PROOF'", '''
        report['freshness_final']=state['face_targets']['freshness_metrics']
        ages=[row['face_targets']['source_age_ms'] for row in report['samples']]
        report['sampled_freshness']={'samples':len(ages),'maximum_ms':max(ages),
            'at_or_over_ttl':sum(age>=1000 for age in ages),'scope':'sparse supervision; not per-publication coverage'}
        report['throughput_and_protection_passed']=True
        report['passed']=True;report['observation_status']='FRESHNESS_1MS_120S_DIAGNOSTIC_NOT_RETRY_OR_SPEEDUP_PROOF'
''')
replace("assert digest(path)==report['candidate_ui_sha256']", "assert digest(path)==report['candidate_ui_sha256']\n        assert digest(face_source)==report['freshness_wiring_sha256']\n        for name,expected in FRESHNESS_HASHES.items():assert digest(candidate/name)==expected")
prefix='FRESHNESS_PAYLOAD='+repr({name:base64.b64encode(gzip.compress(data,mtime=0)).decode() for name,data in files.items()})+'\nFRESHNESS_HASHES='+repr(hashes)+'\n'
source=prefix+source
# gzip/base64 are used before the original function's locally imported base64.
source=source.replace('    import gzip\n    for name,encoded in FRESHNESS_PAYLOAD.items():',
    '    import gzip,base64\n    for name,encoded in FRESHNESS_PAYLOAD.items():')
source=source.replace('aura-face-freshness-metrics-1','aura-face-freshness-light-1')
marker="    before=camera();healthy(before);single_owner(before['pid']);idle=ui_idle()"
assert source.count(marker)==1
source=source.replace(marker,marker+"\n    cost=json.loads(Path('/home/root/aura-post-power-20261022/synthetic/d08603d67f3bf3a4/report.json').read_text())\n    assert cost['passed'] and cost['assessment']['passed']\n    assert cost['source_sha256']['candidate/aura/board/identity/face_freshness_metrics.py']==FRESHNESS_HASHES['board/identity/face_freshness_metrics.py']")
ast.parse(source)
target=HELPERS/'board_postpower_light_live_usb3_20261022.py'
if target.exists():assert target.read_text()==source
else:target.write_text(source)
manifest={'helper':str(target),'sha256':hashlib.sha256(source.encode()).hexdigest(),
 'boot':'7924ac9f-311d-4fcd-98be-57bf023cf1aa','observer_hashes':hashes,'seconds':120,
 'gil_seconds':.001,'cpu_affinity_changed':False,'retry_enabled':False,'protection_30ms_5ms_unchanged':True}
manifest['wrapper_sha256']=hashlib.sha256(wrapper.encode()).hexdigest()
(ROOT/'metrics-live-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest))
