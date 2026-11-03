"""Check the privacy boundary and read-only transport without contacting board."""
import ast
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
source=HERE/'observe_joint_readonly.py'
tree=ast.parse(source.read_text(encoding='utf-8'))
requests=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='request']
assert len(requests)==1 and isinstance(requests[0].args[0],ast.Constant) and requests[0].args[0].value=='GET'
assert not any(isinstance(node,ast.Import) and any(name.name in ('subprocess','ctypes','sqlite3','gi') for name in node.names) for node in ast.walk(tree))
assert not any(isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in ('write_text','write_bytes','unlink','rename','replace','chmod','mkdir') for node in ast.walk(tree))
spec=importlib.util.spec_from_file_location('readonly_observer_offline',source)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
secret='DO_NOT_EXPORT_PRIVATE_SENTENCE_83c1'
sample=module.project_gui({'sequence':3,'phase':'SPEAKING','ui_page':'main',
    'body':secret,'reply':secret,'identity':{'name':secret},
    'local_transcription':{'request_id':'public-random-job-id','text':secret},
    'local_recording':{'result':{'text':secret,'sample_count':32000}},
    'board_business':{'dialogue':{'latency':{'asr_ms':100,'unwanted_body':secret,'prepare':{'llm_rpc_ms':250,'response':secret}},
        'last_playback_ack':{'request_id':'public-random-job-id','committed':True,'reply':secret}},
        'memory':{'running':True,'completed':3,'error':secret}},
    'manual_pan':{'history':[secret],'readback':{'flags':0,'name':secret}}})
serialized=json.dumps(sample)
assert secret not in serialized and 'public-random-job-id' not in serialized
assert sample['latency']['asr_ms']==100 and sample['ack']['committed'] is True
assert sample['turn_hash']==sample['ack']['turn_hash']
assert sample['microphone_open'] is None and sample['gui_fault_count'] is None
assert sample['memory']['error_present'] is True
camera=module.project_camera({'pid':9,'identity':{'ready':True,'name':secret,'feature_inference':{'completed':2,'text':secret}},'dpu_schedule':{'primary_calls':20,'owner_fenced':False,'private':secret}})
assert secret not in json.dumps(camera) and camera['native']['primary_calls']==20
assert camera['source']['capture_frames'] is None
result={'remote_network_called':False,'remote_controls_called':False,
    'checks':['only GET request exists','no subprocess/device/database imports in remote observer',
        'no remote write methods','private text/name/media fields omitted',
        'request identifiers hashed','missing fields remain unknown',
        'playback ACK and turn hash association retained','camera counters preserved'],
    'status':'PASS','checks_count':8}
(HERE/'OFFLINE_OBSERVER_CHECK.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
