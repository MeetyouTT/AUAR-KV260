"""Clone the current GUI and prepare a bounded manual release; no service change."""
import ast,base64,copy,gzip,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path

sys.dont_write_bytecode=True
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def need(value,message):
    if not value:raise RuntimeError(message)

need(os.uname().machine=='aarch64' and os.geteuid()==0,'Board root required')
data=gzip.decompress(base64.b64decode(PAYLOAD))
need(hashlib.sha256(data).hexdigest()==PAYLOAD_SHA,'UI payload changed')
content=json.loads(data);meta=content['meta'];base=meta['baseline']
need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==base['boot'],'Boot changed')
need(sha(base['launcher_path'])==base['launcher_sha256'] and sha(base['startup_config_path'])==base['startup_config_sha256'],'Existing GUI launch changed')
root=Path(meta['root']);need(root.parent==Path('/home/root/aura-pan-ui-v2-20261024'),'Wrong UI release root')
need(not root.exists(),'UI release already prepared')
root.mkdir(parents=True,mode=0o700);runtime=root/'runtime';runtime.mkdir()
old=Path(base['startup_config']['runtime'])
excluded={'stage.log','managed-runs','launch.json','__pycache__'}
def clone(source,target,config_tree=False):
    for p in source.iterdir():
        if p.name in excluded or p.suffix=='.pyc':continue
        q=target/p.name
        if p.is_symlink():
            if p.name=='config' and p.is_dir():
                q.mkdir();clone(p.resolve(),q,True)
            else:q.symlink_to(p.resolve(strict=True),target_is_directory=p.is_dir())
        elif p.is_dir():q.mkdir();clone(p,q,config_tree)
        else:shutil.copy2(p,q)
clone(old,runtime)
manifest_before={str(p.relative_to(old/'aura')):sha(p) for p in (old/'aura').rglob('*.py') if not p.is_symlink()}
need(manifest_before==meta['baseline_python_sha256'],'Current GUI Python tree changed')
for name,record in content['files'].items():
    raw=base64.b64decode(record['base64']);need(hashlib.sha256(raw).hexdigest()==record['sha256'],'Patch differs')
    relative=Path(name);need(not relative.is_absolute() and '..' not in relative.parts,'Patch path outside release')
    target=root/relative;target.parent.mkdir(parents=True,exist_ok=True)
    need(target.parent.resolve()==target.parent and not target.is_symlink(),'Patch target redirects')
    if target.suffix=='.py':ast.parse(raw)
    target.write_bytes(raw)
release_root=root/'manual-release';release_root.mkdir(exist_ok=True)
board_trial=Path('/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2')
board_manifest=json.loads((board_trial/'candidate-manifest.json').read_text())
need(sha(board_trial/'candidate-manifest.json')==meta['board_candidate_manifest_sha256'],'Hardware candidate changed')
for name,pin in board_manifest['runtime_files'].items():need(sha(name)==pin,'Installed hardware differs')
shutil.copy2(board_trial/'driver/libvsrv.so',release_root/'libvsrv.so')
for name in ['vsrv_driver.py','vsrv_transport.py']:shutil.copy2(runtime/'aura/board/motion'/name,release_root/name)
release={'schema_version':1,'status':'OBSERVED_MANUAL_VSRV2','scope':'finite_manual_only',
    'app':'aura-visual-servo-b4096-v2','abi':2,'build_id':0x778d2512,'boot_id':base['boot'],
    'manual_minimum_us':1425,'manual_maximum_us':1445,'external_waveform_verified':False,
    'physical_servo_response_verified':True,'dpu_coexistence_verified':True,
    'automatic_following_enabled':False,'mechanical_reference_calibrated':False,
    'payload_files':{n:sha(release_root/n) for n in ['libvsrv.so','vsrv_driver.py','vsrv_transport.py']},
    'runtime_files':board_manifest['runtime_files'],
    'trial_sha256':sha(release_root/'observed-trial.json'),
    'observation_sha256':sha(release_root/'human-observation.json')}
need(release['payload_files']['libvsrv.so']==board_manifest['payload_files']['libvsrv.so'],'Native library pairing changed')
manifest=release_root/'release.json';manifest.write_text(json.dumps(release,indent=2)+'\n')
config={'enabled':True,'boot_id':base['boot'],'fdt_sha256':base['fdt_sha256'],
    'release_manifest':str(manifest),'release_manifest_sha256':sha(manifest),
    'manual_minimum_us':1425,'manual_maximum_us':1445,'maximum_step_us':20,'maximum_duration_s':2}
pan_config=runtime/'aura/config/pan_manual.local.json';pan_config.write_text(json.dumps(config,indent=2)+'\n')
startup=root/'startup';startup.mkdir();shutil.copy2(base['launcher_path'],startup/'launcher.py')
gui_config=copy.deepcopy(base['startup_config']);gui_config['runtime']=str(runtime)
patch_names=[n[len('runtime/aura/'):] for n in content['files'] if n.startswith('runtime/aura/')]
for name in patch_names+['config/pan_manual.local.json']:
    gui_config['component_sha256'][name]=sha(runtime/'aura'/name)
(startup/'config.json').write_text(json.dumps(gui_config,indent=2)+'\n')
after={str(p.relative_to(runtime/'aura')):sha(p) for p in (runtime/'aura').rglob('*.py') if not p.is_symlink()}
changed=[n for n,pin in manifest_before.items() if after.get(n)!=pin]
new=[n for n in after if n not in manifest_before]
need(set(changed+new)==set(patch_names),'Unexpected Python changes in clone')
env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(runtime/'aura'))
check=subprocess.run(['/usr/bin/python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],env=env,capture_output=True,text=True,timeout=20)
need(check.returncode==0,'New GUI launch preflight failed: '+check.stderr[-1200:])
code='from board.motion.manual_vsrv import load_release\nimport json\nfrom pathlib import Path\nc=json.loads(Path('+repr(str(pan_config))+').read_text());root,release=load_release(c);print(release["status"])'
check=subprocess.run(['/usr/bin/python3','-B','-c',code],env=env,capture_output=True,text=True,timeout=10)
need(check.returncode==0,'Manual evidence gate failed: '+check.stderr[-1200:])
summary={'prepared':True,'root':str(root),'runtime':str(runtime),'startup':str(startup),
    'gui_python_before':len(manifest_before),'gui_python_after':len(after),'changed_python':changed,'added_python':new,
    'source_before':manifest_before,'source_after':after,'startup_config_sha256':sha(startup/'config.json'),
    'launcher_sha256':sha(startup/'launcher.py'),'manual_release_sha256':sha(manifest),
    'existing_gui_runtime':str(old),'existing_gui_untouched':True,'services_changed':False,
    'mmio_opened':False,'ARM_sent':False,'COMMIT_sent':False,
    'manual_minimum_us':1425,'manual_maximum_us':1445,'maximum_duration_s':2,
    'external_waveform_verified':False,'observed_manual_scope_only':True}
(root/'prepared.json').write_text(json.dumps(summary,indent=2)+'\n')
(root/'meta.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ['source_before','source_after']}))
