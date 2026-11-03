"""Build public source payload and review metadata only. No board connection."""
import ast
import base64
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
names=('board/interaction/ui_services.py','tools/board_camera_preview.py')
components={}
for name in names:
    old=(HERE/'original'/name).read_bytes();new=(HERE/'candidate'/name).read_bytes()
    components[name]={'old_sha256':hashlib.sha256(old).hexdigest(),'new_sha256':hashlib.sha256(new).hexdigest(),
        'new_bytes_base64':base64.b64encode(new).decode()}
payload=(json.dumps({'schema':'aura-ui-preview-projection-payload-1','components':components},indent=2)+'\n').encode()
payload_path=HERE/'transaction_payload.json'
if payload_path.exists():assert payload_path.read_bytes()==payload
else:
    with payload_path.open('xb') as stream:stream.write(payload)
script=(HERE/'transaction_preview_projection.py').read_bytes();code=script.decode().replace('\r\n','\n')
tree=ast.parse(code)
calls=[node for node in ast.walk(tree) if isinstance(node,ast.Call)]
requirement={
    'default_dry_run':"parser.add_argument('--apply',action='store_true')" in code,
    'no_ssh_or_network_imports':not any(isinstance(node,(ast.Import,ast.ImportFrom)) and any(term in ast.get_source_segment(code,node) for term in ('paramiko','socket','http.client','urllib')) for node in ast.walk(tree)),
    'systemctl_only_show':"['systemctl','show',name," in code and "'start'" not in code and "'stop'" not in code,
    'exclusive_create': 'os.O_EXCL' in code and 'os.O_NOFOLLOW' in code,
    'fsync_and_atomic_startup_replacement':'os.fsync' in code and 'os.replace(stage,path)' in code,
    'selected_dependency_hold':'HOLD_SELECTED_READBACK_PINS_MODIFIED_COMPONENT' in code,
    'no_recursive_delete':not any(isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in ('rmtree','remove','unlink') for node in ast.walk(tree)),
    'original_380_verified':"len(pins)==380" in code,
    'pan25_verified':"len(files)==25" in code,
    'rollback_rebases_only_target_pins':'startup_after(context[\'startup\'],desired)' in code}
assert all(requirement.values()),requirement
review={'status':'LOCAL_TEMPLATE_ONLY_NOT_EXECUTED','script_sha256':hashlib.sha256(script).hexdigest(),
    'script_sha256_lf':hashlib.sha256(code.encode()).hexdigest(),'payload_sha256':hashlib.sha256(payload).hexdigest(),
    'payload_bytes':len(payload),'components':{name:{key:value for key,value in row.items() if key!='new_bytes_base64'} for name,row in components.items()},
    'static_checks':requirement,
    'runtime_mutations':['<fresh runtime>/aura/board/interaction/ui_services.py','<fresh runtime>/aura/tools/board_camera_preview.py','<fresh expected startup path>'],
    'supporting_mutations':['<startup parent>/.gtk-preview-cpu-deploy.lock','<dedicated transaction>/intent.json','<dedicated transaction>/plan.json','<dedicated transaction>/backup/*','<dedicated transaction>/startup.after.json','<dedicated transaction>/receipt.json','one O_EXCL stage file beside each replaced target; consumed by os.replace'],
    'never_mutated':['private databases','model files','camera configuration or process','selected readback source map','all pan files and controller25','all unrelated startup fields and component pins'],
    'not_an_atomic_multifile_transaction':'Current writer freeze remains mandatory. Cooperative flock and repeated content+inode+mtime CAS reject observed conflicts; POSIX file replacement alone cannot prevent a noncooperating writer in the final check/rename interval.',
    'on_failure':'HOLD, no automatic retry or rollback; inspect fresh current known bytes and explicitly run rollback.'}
review_path=HERE/'TRANSACTION_REVIEW.json'
if review_path.exists():
    previous=review_path.read_bytes()
    backup=HERE/('TRANSACTION_REVIEW.before_'+hashlib.sha256(previous).hexdigest()[:12]+'.json')
    if not backup.exists():
        with backup.open('xb') as stream:stream.write(previous)
with review_path.open('w',encoding='utf-8') as stream:json.dump(review,stream,indent=2)
print(json.dumps(review))
