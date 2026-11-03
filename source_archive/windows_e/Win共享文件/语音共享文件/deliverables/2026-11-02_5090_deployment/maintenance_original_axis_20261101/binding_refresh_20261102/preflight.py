"""Read only the original metadata needed to rebase the original pan transaction."""
import ast,copy,hashlib,http.client,json,os,subprocess,time
from pathlib import Path
B=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');A=B/'runtime/aura';S=B/'startup/config.json'
def raw(p):
    p=Path(p);assert p.is_file() and not p.is_symlink() and p.suffix not in ('.db','.sqlite','.sqlite3') and p.stat().st_size<64000000
    return p.read_bytes()
def sha(p):return hashlib.sha256(raw(p)).hexdigest()
def load(p):return json.loads(raw(p))
def unit(n):
    r=subprocess.run(['systemctl','show',n,'--property=MainPID,ActiveState,SubState,Job,Result'],capture_output=True,text=True,timeout=5);assert r.returncode==0
    return dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==G['boot_id']
assert sha(S)==G['startup_before_sha256'];startup=load(S);assert startup['component_sha256']==C['pins'] and len(C['pins'])==380
assert all(sha(A/n)==v for n,v in C['pins'].items())
assert all(C['pins'][n]==v for n,v in G['latest_identity_four_core'].items())
gui=unit('aura-avatar-ui.service');assert gui['MainPID']=='0' and gui['ActiveState']=='inactive' and gui['SubState']=='dead' and not gui['Job']
camera=unit('aura-camera-ui.service');assert camera['MainPID']==str(G['camera_owner']['pid']) and camera['ActiveState']=='active' and camera['SubState']=='running' and not camera['Job']
p=Path('/proc')/str(G['camera_owner']['pid']);assert (p/'stat').read_text().rsplit(')',1)[1].split()[19]==G['camera_owner']['birth_ticks']
assert hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()==G['camera_owner']['command_sha256']
assert sha(G['camera_config']['path'])==G['camera_config']['sha256']
assert sha('/sys/firmware/fdt')==C['context']['fdt_sha256']
assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()==C['context']['firmware_name']=='aura-visual-servo-b4096-wide-v1.bit.bin'
assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
assert Path('/etc/vart.conf').read_bytes()==b'firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-wide-v1/aura-visual-servo-b4096-wide-v1.xclbin\n'
restore=Path(C['wide_root']);assert load(restore/'wide-context.json')==C['context']
assert sha(restore/'id-stop.json')==C['IDSTOP_sha256'];stop=load(restore/'id-stop.json');verified=load(restore/'idstop-verified.json')
assert verified['report_sha256']==C['IDSTOP_sha256'] and verified['report']==stop and stop['identity_stop_passed']
ui=load(A/'config/board_avatar_gtk.json');spec=ui['board_business']['face_readback'];selected=load(G['selected_face_binding']['path'])
assert spec['path']==G['selected_face_binding']['path'] and spec['sha256']==sha(spec['path'])==G['selected_face_binding']['sha256']
assert selected['source_sha256']==C['selected_sources'] and len(C['selected_sources'])==27
assert all(sha(n)==v for n,v in C['selected_sources'].items())
assert selected['board_boot_id']==G['boot_id'] and selected['camera_pid']==G['camera_owner']['pid'] and str(selected['camera_start_ticks'])==G['camera_owner']['birth_ticks'] and selected['camera_config']==G['camera_config']['path']
verifier=A/'board/runtime/audio/face_gallery_readback.py';tree=ast.parse(raw(verifier).decode());klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='FaceGalleryReadback');node=copy.deepcopy(next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='_verify'));node.decorator_list=[]
space={'Path':Path,'hashlib':hashlib,'json':json};exec(compile(ast.Module(body=[node],type_ignores=[]),str(verifier)+'::<metadata-only>', 'exec'),space);space['_verify'](selected)
face=load(A/'config/pan_face.local.json');manual=load(A/'config/pan_manual.local.json');direction=load(A/'config/pan_direction.current.json')
control=Path(face['release_root']);assert str(control)=='/home/root/aura-pan-wide-20261028/control-10282601-left40-right45-stable150-35d5e154'
assert sha(control/'deployment-manifest.json')==face['manifest_sha256']=='9cd35b967bf9c859ed3f1f4de4dc5dad199e81ddfed845435fc8745a41be0ba9'
files=load(control/'deployment-manifest.json')['files'];assert len(files)==25
for f in files:assert sha(f['destination'])==f['sha256'] and Path(f['destination']).stat().st_size==f['bytes']
release_path=Path(manual['release_manifest']);assert sha(release_path)==manual['release_manifest_sha256'];release=load(release_path)
assert release['status']=='USER_RATED_RANGE_VSRV2';auth_path=release_path.parent/release['authorization']['file'];assert sha(auth_path)==release['authorization']['sha256']
zone_path=Path(face['arguments']['zone-settings']);zone=load(zone_path)
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:maps=(proc/'maps').read_text()
    except (FileNotFoundError,ProcessLookupError):continue
    assert 'libvsrv.so' not in maps and '/dev/mem' not in maps,'Existing original axis owner'
c=http.client.HTTPConnection('127.0.0.1',8790,timeout=3)
try:
    c.request('GET','/health');r=c.getresponse();body=r.read(2097153);assert r.status==200 and len(body)<=2097152;health=json.loads(body)
finally:c.close()
assert health['pid']==G['camera_owner']['pid'] and health['board_boot_id']==G['boot_id'] and health['identity']['ready'] is True
assert not any(health.get(k) for k in ('camera_error','detector_error','preview_error')) and health['motion_command_emitted'] is False
print(json.dumps({'status':'ORIGINAL_PAN_METADATA_FRESH_INPUTS_VERIFIED','boot_id':G['boot_id'],'startup_sha256':sha(S),'camera_owner':G['camera_owner'],'GUI':gui,'source380_verified':True,'control25_verified':True,'four_core_verified':True,'selected27_original_verify_passed':True,'pan':{'face':face,'manual':manual,'direction':direction},'old_manual_release_sha256':sha(release_path),'old_authorization':load(auth_path),'old_authorization_pin':{'path':str(auth_path),'sha256':sha(auth_path)},'zone':zone,'zone_sha256':sha(zone_path),'context':C['context'],'checkpoint_or_MMIO_or_services_touched':False,'observation_monotonic_ms':round(time.monotonic()*1000)}))
