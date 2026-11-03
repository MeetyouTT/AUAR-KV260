"""Add the validated coordination protocol to the unchanged recovery payload."""
import ast,base64,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
parent=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_recovery50_live_r2_20261023.py')
raw=parent.read_bytes();assert hashlib.sha256(raw).hexdigest()=='10261c1b5b2b745877121c90d940be80e67f91ae57a524ed2040a1f52af4f65c'
source=raw.decode();original_tree=ast.parse(source)
module=(ROOT/'handoff.py').read_bytes();module_sha=hashlib.sha256(module).hexdigest()
assert module_sha=='12a6a4ea98f33926465d3e0cb6ae046cf3a82f29fbaa8021d4beaad249f9c734'
prefix='HANDOFF_SHA='+repr(module_sha)+'\nHANDOFF_DATA='+repr(base64.b64encode(gzip.compress(module,mtime=0)).decode())+'\n'
functions='''def prepare_handoff(wrapper,updated,candidate):
    import importlib.util,base64,gzip
    root=Path('/home/root/aura-coordinated-switch-20261023')/('recovery50-'+str(os.getpid()))
    root.mkdir(parents=True,exist_ok=False,mode=0o700);assert root.resolve()==root
    data=gzip.decompress(base64.b64decode(HANDOFF_DATA));assert hashlib.sha256(data).hexdigest()==HANDOFF_SHA
    module_path=root/'handoff.py';module_path.write_bytes(data);module_path.chmod(0o600)
    spec=importlib.util.spec_from_file_location('_owned_trial_coordination',module_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    ops=module.BoardOps(root);ops.capture(wrapper)
    target=root/'camera.candidate';target.write_bytes(updated);target.chmod(0o600)
    ops.meta['unit_hashes']['candidate']=hashlib.sha256(updated).hexdigest()
    ops.meta['runtimes']['candidate']=str(candidate);ops.save_meta()
    return ops,module

def rollback_source(root):
    return """import hashlib,importlib.util,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(ROOT_VALUE);p=root/'handoff.py'
assert root.resolve()==root and root.parent==Path('/home/root/aura-coordinated-switch-20261023')
assert hashlib.sha256(p.read_bytes()).hexdigest()==SHA_VALUE
spec=importlib.util.spec_from_file_location('_independent_coordinated_restore',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
print(json.dumps(m.BoardOps(root).restore()))
""".replace('ROOT_VALUE',repr(str(root))).replace('SHA_VALUE',repr(HANDOFF_SHA))

'''
old=next(n for n in original_tree.body if isinstance(n,ast.FunctionDef) and n.name=='rollback_source')
lines=source.splitlines(keepends=True);lines[old.lineno-1:old.end_lineno]=[functions]
source=''.join(lines)
def replace(old,new):
    global source
    assert source.count(old)==1,(old[:100],source.count(old))
    source=source.replace(old,new)
replace("    (folder/'rollback.py').write_text(rollback_source(folder))", """    coordinator,coordination=prepare_handoff(Path(__file__).resolve(),updated,candidate)
    timer='aura-coordinated-recovery50-rollback-'+str(os.getpid())
    coordinator.meta['guard']=timer;coordinator.save_meta()
    (folder/'rollback.py').write_text(rollback_source(coordinator.folder))""")
replace("timer='aura-postpower-recovery50-r2-live-rollback-'+str(os.getpid());report['timer']=timer",
        "report['timer']=timer;report['handoff_root']=str(coordinator.folder)")
replace("    armed=True\n    try:", "    armed=True\n    coordinator.meta['guard_armed']=True;coordinator.save_meta();coordinator.assert_guard_armed()\n    try:")
replace("""        service('stop','aura-camera-ui.service');assert UNIT.read_bytes()==original_unit
        atomic(UNIT,updated);service('daemon-reload');service('start','--no-block','aura-camera-ui.service')""",
        """        coordination.transition(coordinator,'candidate')
        unit_pids['aura-avatar-ui.service']=service('show','aura-avatar-ui.service','-p','MainPID','--value').strip()
        cursor=coordinator.meta['quiescent_cursor']""")
replace("command(['/usr/bin/python3','-B',str(folder/'rollback.py')],timeout=70)",
        "command(['/usr/bin/python3','-B',str(folder/'rollback.py')],timeout=300)")
replace("""            for p,expected in protected.items():assert digest(p)==expected
            for name,pid in unit_pids.items():assert service('show',name,'-p','MainPID','--value').strip()==pid
            report['restored']=restored;report['rollback_verified']=True
            service('stop',timer+'.timer');armed=False""", """            for p,expected in protected.items():assert digest(p)==expected
            coordinator.meta=json.loads((coordinator.folder/'session.json').read_text())
            coordinator.verify();assert coordinator.ready('original')
            for name,pid in unit_pids.items():
                if name!='aura-avatar-ui.service':assert service('show',name,'-p','MainPID','--value').strip()==pid
            report['protected_audio_source_verified']=True
            report['restored_audio_pid']=service('show','aura-avatar-ui.service','-p','MainPID','--value').strip()
            report['restored']=restored;report['rollback_verified']=True
            service('stop',timer+'.timer');armed=False
            coordinator.meta['guard_armed']=False;coordinator.save_meta()""")
replace('--on-active=360s','--on-active=600s')
replace('--property=RuntimeMaxSec=300','--property=RuntimeMaxSec=540')
replace('YUNET_RECOVERY50_GAP3_1MS_DUAL_MODEL_120S_ALWAYS_RESTORED',
        'COORDINATED_RECOVERY50_GAP3_1MS_DUAL_MODEL_120S_ALWAYS_RESTORED')
replace("folder=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live')/('recovery50-'+str(os.getpid()))",
        "folder=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live')/('coordinated50-'+str(os.getpid()))")
replace('postpower-recovery50-r2-launches','postpower-coordinated50-launches')
replace("unit='aura-postpower-recovery50-r2-live-'+key", "unit='aura-postpower-coordinated50-live-'+key")
source=prefix+source
tree=ast.parse(source)
def constants(t):
    return {n.targets[0].id:ast.literal_eval(n.value) for n in t.body if isinstance(n,ast.Assign)
            and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('RETRY_PAYLOAD','RETRY_HASHES','RETRY_WRAPPER','RETRY_WRAPPER_SHA')}
assert constants(tree)==constants(original_tree),'Native/recovery payload and GIL wrapper must stay identical'
main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='rollback_source'
               and any(isinstance(a,ast.Name) and a.id=='folder' for a in n.args) for n in ast.walk(main))
target=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_coordinated_recovery50_r2_20261023.py')
assert not target.exists();target.write_text(source)
result={'helper':str(target),'sha256':hashlib.sha256(source.encode()).hexdigest(),'handoff_sha256':module_sha,
        'parent_sha256':hashlib.sha256(raw).hexdigest(),'recovery_payload_unchanged':True,
        'restore_protocol':'coordinated audio/camera with source/config/preference/health verification',
        'successful_gui_pid_change_expected':True,'xserver_pid_change_allowed':False,
        'software_tests':89,'handoff_tests':16,'seconds':120,'runtime_max_s':540,'independent_restore_s':600}
(ROOT/'coordinated-recovery50-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
