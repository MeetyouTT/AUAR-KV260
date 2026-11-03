"""Adapt the reviewed read-only preflight to the actually applied one-component GUI release."""
import ast
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]
BASE=OUT/'parallel_platform/collect_preflight_readonly.py'
source=BASE.read_text(encoding='utf-8')
source=source.replace("STARTUP_SHA = '07c5aa3b1c8da060e5a7d8520021bce7f167a8cf303b48a0a24f8e2a8b63035d'",
                      "STARTUP_SHA = '0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f'")
source=source.replace('import datetime\n','import ast\nimport copy\nimport datetime\nimport re\n',1)
marker="    return result\n\nboot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()"
assert marker in source
enhance="""    result['native_public_counter_recovery_tree'] = public_counters(s)
    result['feature_public_counter_tree'] = public_counters(feature)
    result['face_public_counter_tree'] = public_counters(face)
    counter_keys = ('requests','execution_attempts','completed','features_returned','deferred','slot_denials','expired_after_admission')
    result['sface_seven_counters'] = {key: feature.get(key) for key in counter_keys}
    result['sface_seven_counter_fields_available'] = [key for key in counter_keys if type(feature.get(key)) is int]
    result['observed_mono_ns'] = time.monotonic_ns()
    return result

COUNTER_FIELDS = {
    'abi_version','native_abi','native_critical','owner_fenced','quiesced','primary_calls','primary_period_overruns',
    'primary_waiting','active','fenced','admissions','overruns','completed','native_failures','not_submitted','disabled',
    'pending_result_tokens','enabled','phase','reason','faults','attempts','recoveries','attempt_count','opaque_attempt_count',
    'history_opaque','observed_ns','cooldown_until_ns','fault_primary_calls','fault_primary_overruns','probe_successes','attempt_times_ns',
    'requests','execution_attempts','features_returned','deferred','slot_denials','expired_after_admission',
    'processed','discarded','pending_frames','dpu_submissions','submitted','execution_count','successes','failures',
    'task','blocked','admitted','deadline_rejects','slot_denied','period_overruns','inherited_overruns','inherited_disabled',
    'native_health_calls','native_health_failures','primary_deadline_misses','source_pid','source_birth_ticks',
}
ENUMS = {'READY','FAULTED','COOLDOWN','PROBING','DISABLED','IDLE','WAITING','ACTIVE','RUNNING','NONE','ARMED'}
def public_counters(value):
    if isinstance(value,dict):
        result={}
        for key,item in value.items():
            if not isinstance(key,str) or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',key) is None: continue
            if key in COUNTER_FIELDS and (type(item) in (bool,int) or isinstance(item,list) and all(type(v) in (bool,int) for v in item)):
                result[key]=item
            elif key in COUNTER_FIELDS and type(item) is str and item in ENUMS:
                result[key]=item
            elif isinstance(item,(dict,list)):
                projected=public_counters(item)
                if projected not in ({},[]):result[key]=projected
        return result
    if isinstance(value,list):
        return [public_counters(item) for item in value if isinstance(item,(dict,list))]
    return {}

boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()"""
source=source.replace(marker,enhance)
old="""assert gui['MainPID'] == '0' and not gui.get('Job'), 'GUI owner appeared'
"""
new="""assert gui['MainPID'] == '0' and not gui.get('Job'), 'GUI owner appeared'
assert gui['ActiveState']=='inactive' and gui['SubState']=='dead' and gui['Result']=='success'
assert gui['ExecMainStatus']=='0'
"""
assert old in source;source=source.replace(old,new)
marker="native_manifest = CAMERA_AURA.parent / 'camera-python-manifest.json'"
selected="""aura=runtime/'aura'
assert digest(aura/'tools/unified_identity_binding.py')=='85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809'
assert digest(aura/'config/board_avatar_gtk.json')=='fc21e6f2ef831442b08966957fa7aeb744a9b74124ee8778edc40397285626cd'
assert digest(aura/'config/face_gallery_readback.local.json')=='e203e6ffe973397464791eb07f12e0bd0c24658988c119e9d7d75685c4e41986'
gui_spec=document(aura/'config/board_avatar_gtk.json')['board_business']['face_readback']
selected_sha='4d8f0c2bccea1c7a56761fbcb204f40ba3b3c2fc9efad76af778aff535d378ac'
assert gui_spec['sha256']==digest(gui_spec['path'])==selected_sha
selected=document(gui_spec['path']);assert len(selected['source_sha256'])==24
assert all(digest(path)==sha for path,sha in selected['source_sha256'].items())
assert selected['board_boot_id']==BOOT and selected['camera_pid']==CAMERA_PID
assert int(selected['camera_start_ticks'])==CAMERA_BIRTH and selected['camera_cmdline_sha256']==CAMERA_CMD
verifier=aura/'board/runtime/audio/face_gallery_readback.py'
assert digest(verifier)=='b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e'
tree=ast.parse(regular(verifier).decode())
klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FaceGalleryReadback')
node=copy.deepcopy(next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='_verify'));node.decorator_list=[]
space={'Path':Path,'hashlib':hashlib,'json':json}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(verifier)+'::<metadata-only-_verify>','exec'),space)
space['_verify'](selected)
settings=document(OPS/'pan-face-edge-v5/native-operator-v1/settings.json')
assert settings['unit_sha256']=='7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32'
native_manifest = CAMERA_AURA.parent / 'camera-python-manifest.json'"""
assert marker in source;source=source.replace(marker,selected)
source=source.replace("operator_files = document(operator_manifest)['files']","operator_files = document(operator_manifest)['files']\nassert len(operator_files)==7")
source=source.replace("manifest = document(RELEASE / 'candidate-manifest.json')","manifest = document(RELEASE / 'candidate-manifest.json')\nassert len(manifest['runtime_files'])==4 and len(manifest['payload_files'])==3")
source=source.replace("assert native_actual == native_files['files'], 'Full original Native Python closure differs'",
    "assert native_actual == native_files['files'] and len(native_actual)==222, 'Full original Native Python closure differs'")
source=source.replace("    'camera_source_files_verified': len(readback['source_sha256']), 'camera_owner': current_owner,",
    "    'default_camera_source_files_verified': len(readback['source_sha256']), 'camera_owner': current_owner,\n    'selected_binding_sha256':selected_sha,'selected_camera_source_files_verified':len(selected['source_sha256']),\n    'selected_original_verifier_passed':True,'source_unit_sha256':settings['unit_sha256'],")
source=source.replace("    'platform_switch_permitted': False, 'final_checkpoint_created_or_fabricated': False,",
    "    'prestop_counter_lower_bound_observed_mono_ns':samples[-1]['observed_mono_ns'],\n    'prestop_counter_lower_bounds':samples[-1],\n    'platform_switch_permitted': False, 'final_checkpoint_created_or_fabricated': False,")
ast.parse(source)
target=HERE/'collect_current_prestop_readonly.py'
with target.open('x',encoding='utf-8',newline='\n') as stream:stream.write(source)
transport=HERE.parents[2]/'2026-10-18_board_dialogue/board_ssh.py'
spec=importlib.util.spec_from_file_location('prestop_checkpoint_readonly_ssh',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=json.loads(module.ssh('python3 -B -',source,timeout=90))
output=HERE/'prestop_current_01.json'
with output.open('x',encoding='utf-8') as stream:
    json.dump({'host_observed_start_utc':start,'host_observed_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reused_preflight_source_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'transport_sha256':hashlib.sha256(transport.read_bytes()).hexdigest(),
        'actual_identity_query_applied_receipt_sha256':hashlib.sha256((OUT/'maintenance_original_axis_20261101/identity_query_applied.json').read_bytes()).hexdigest(),
        'board_result':result},stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps({'output':str(output),'phase':result['phase'],'lower_bounds':result['prestop_counter_lower_bounds'],
                  'board_mutations':False},ensure_ascii=False))
