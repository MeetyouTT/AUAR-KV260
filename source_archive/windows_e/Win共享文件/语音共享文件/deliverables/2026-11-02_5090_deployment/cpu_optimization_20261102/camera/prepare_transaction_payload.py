"""Prepare six-file camera release payload locally; never applies it.

The caller supplies the six fresh, hash-checked public source/config bytes and
the SHA of the NEW final checkpoint obtained by a normal current-owner stop.
No checkpoint contents, state directory, model or database is copied here.
"""
import argparse,copy,hashlib,json,re
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT='/home/root/aura-native-live-20261024'
CANDIDATE_ROOT=ROOT+'/candidates/native-r4-metrics-fix'
OPS=ROOT+'/ops/be72669aa53de735'
OP=OPS+'/pan-face-edge-v5/native-operator-v1'
UNIT='7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32'
UI_SHA='7d4773b8ff527773eefc90aa2443dd4bfae801f07c6fcde672af65dd22ff8f66'
OLD_UI='9d714b9bd00ea1da12088fa1e22100d7bdb689d0cac10332c3933b31e4f4d2df'
TARGETS={
 'ui_camera_service.py':CANDIDATE_ROOT+'/aura/board/vision/ui_camera_service.py',
 'camera-python-manifest.json':CANDIDATE_ROOT+'/camera-python-manifest.json',
 'board_camera_ui.proposed.json':CANDIDATE_ROOT+'/board_camera_ui.proposed.json',
 'meta.json':OPS+'/meta.json',
 'native_entry_pan_face_v5.py':OPS+'/native_entry_pan_face_v5.py',
 'runtime-manifest.json':OP+'/runtime-manifest.json'}
OLD={
 'ui_camera_service.py':OLD_UI,
 'camera-python-manifest.json':'5e08f7cf587d74334ef24104ea01f79701629b48f2004fb772ce3f8ea82afd0d',
 'board_camera_ui.proposed.json':'e137bbb7894ecebcaadc8e57abc4bd8794c80dc3b9c1f87f09389a53ef88af20',
 'native_entry_pan_face_v5.py':'288f6b7b56702edf45b432686db4f77b156408c0b3f78fd31c05edb33df971c4',
 'runtime-manifest.json':'74e011db30a9d943a9512f7648190ac0c01060af06df1280d1e8ea006dc882ad'}

def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')

def prepare(inputs,expected_meta_sha,fresh_path,fresh_sha):
    assert re.fullmatch('[0-9a-f]{64}',expected_meta_sha)
    assert re.fullmatch('[0-9a-f]{64}',fresh_sha)
    assert set(inputs)==set(TARGETS)
    for name,value in inputs.items():
        assert sha(value)==(expected_meta_sha if name=='meta.json' else OLD[name]),name
    assert fresh_sha!='c6c8baab1de423e27740137330f8315796a7778e36735c93a0c87f2a56029471','Old final was already consumed'
    candidate=(HERE/'candidate_v3/ui_camera_service.py').read_bytes();assert sha(candidate)==UI_SHA
    manifest=json.loads(inputs['camera-python-manifest.json'])
    assert manifest['schema']=='aura-native-python-source-2' and len(manifest['files'])==222
    assert manifest['files']['board/vision/ui_camera_service.py']==OLD_UI
    new_manifest=copy.deepcopy(manifest);new_manifest['files']['board/vision/ui_camera_service.py']=UI_SHA
    manifest_raw=encoded(new_manifest)
    config=json.loads(inputs['board_camera_ui.proposed.json']);new_config=copy.deepcopy(config)
    native=new_config['native_execution']
    assert native['source_manifest']==TARGETS['camera-python-manifest.json']
    assert native['source_manifest_sha256']==OLD['camera-python-manifest.json']
    assert native['source_unit_sha256']=='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
    assert native['library_sha256']=='c675ba698d45acd8742e52403e6186f43dc56d7d313d0e740896b19412bde656'
    assert fresh_path==native['checkpoint_output']==CANDIDATE_ROOT+'/state/native-protection-checkpoint.json'
    native['source_manifest_sha256']=sha(manifest_raw)
    native['seed']={'path':fresh_path,'sha256':fresh_sha}
    config_raw=encoded(new_config)
    meta=json.loads(inputs['meta.json']);new_meta=copy.deepcopy(meta)
    assert meta['candidate_root']==CANDIDATE_ROOT and meta['candidate_config']==TARGETS['board_camera_ui.proposed.json']
    assert meta['candidate_ui_sha256']==OLD_UI
    new_meta['candidate_ui_sha256']=UI_SHA
    for name,value in (('ui_camera_service.py',candidate),('camera-python-manifest.json',manifest_raw),('board_camera_ui.proposed.json',config_raw)):
        assert meta['protected'][TARGETS[name]]==OLD[name]
        new_meta['protected'][TARGETS[name]]=sha(value)
    app=inputs['native_entry_pan_face_v5.py'].decode('utf-8')
    assert app.count(OLD_UI)==1
    app_raw=app.replace(OLD_UI,UI_SHA).encode('utf-8')
    runtime=json.loads(inputs['runtime-manifest.json']);new_runtime=copy.deepcopy(runtime)
    assert len(runtime['files'])==7 and runtime['files'][TARGETS['native_entry_pan_face_v5.py']]==OLD['native_entry_pan_face_v5.py']
    assert runtime['files'][OP+'/source-manifest.json']==UNIT
    assert runtime['files'][OP+'/libaura_native_operator.so']=='704f561a50b5f0fb8f9b4cf72c024acce0cdafd888cad0784507f484518fc224'
    new_runtime['files'][TARGETS['native_entry_pan_face_v5.py']]=sha(app_raw)
    payload={'ui_camera_service.py':candidate,'camera-python-manifest.json':manifest_raw,
        'board_camera_ui.proposed.json':config_raw,'meta.json':encoded(new_meta),
        'native_entry_pan_face_v5.py':app_raw,'runtime-manifest.json':encoded(new_runtime)}
    return payload,{'schema':'aura-camera-lazy-jpeg-six-file-offline-payload-1','candidate_ui_sha256':UI_SHA,
        'files':[{'name':name,'board_path':TARGETS[name],'before_sha256':sha(inputs[name]),'after_sha256':sha(payload[name])} for name in TARGETS],
        'python_source_members':222,'python_changed_members':['board/vision/ui_camera_service.py'],
        'native_C_unit_sha256_unchanged':UNIT,'native_C_files_changed':0,
        'operator_runtime_members':7,'operator_runtime_changed_member':TARGETS['native_entry_pan_face_v5.py'],
        'native_library_sha256_unchanged':'704f561a50b5f0fb8f9b4cf72c024acce0cdafd888cad0784507f484518fc224',
        'fresh_final_seed':{'path':fresh_path,'sha256':fresh_sha},'checkpoint_contents_modified':False,
        'checkpoint_output_unchanged':fresh_path,'service_argv_changed':False,
        'outer_face_source_v17_manifest_unchanged':True,'camera_wrapper_sha256_unchanged':'065c465e0ad0d8cf3ada4b69dcc422a4f85a286b1a7be1536e29d4aeac562df8',
        'board_actions_performed':False,'requires_full_original_byte_backups_outside_python_closure':True,
        'post_camera_start_required':['exact original restore/audit/consumption-marker/counter lower bounds',
            'fresh PID/birth/cmdSHA/run-config path and manifest source hash',
            'new selected readback with actual owner/config and updated changed source pins',
            'original readback verifier and all live Python/Native/operator/UI closure checks',
            'merge fresh UI/identity/voice component pins without reverting any concurrent release'],
        'rollback_rule':'Normal-stop the new owner and consume only its newest fresh final; never restore a consumed predecessor seed or marker.'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-dir',type=Path,required=True)
    parser.add_argument('--expected-meta-sha256',required=True)
    parser.add_argument('--fresh-final-path',required=True)
    parser.add_argument('--fresh-final-sha256',required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    output=args.output_dir.resolve();assert output.is_relative_to(HERE) and not output.exists()
    inputs={name:(args.baseline_dir/name).read_bytes() for name in TARGETS}
    payload,plan=prepare(inputs,args.expected_meta_sha256,args.fresh_final_path,args.fresh_final_sha256)
    output.mkdir()
    for name,value in payload.items():
        with (output/name).open('xb') as stream:stream.write(value)
    with (output/'TRANSACTION_PLAN.json').open('x',encoding='utf-8') as stream:json.dump(plan,stream,indent=2)
    print(json.dumps({'payload_dir':str(output),'files':len(payload),'board_actions_performed':False}))
