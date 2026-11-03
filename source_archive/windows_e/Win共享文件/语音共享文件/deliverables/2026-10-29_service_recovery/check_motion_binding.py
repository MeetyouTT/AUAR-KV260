"""Compare the actual driver's exact platform requirements without importing it."""
import ast,datetime,hashlib,json,re
from recovery_common import H,read,save,ssh
baseline=read('baseline.json')['board'];root=H/'motion_source_snapshot'
source=(root/'board/motion/manual_vsrv.py').read_text(encoding='utf-8')
tree=ast.parse(source)
app=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='APP' for t in n.targets))
ids=re.findall(r"== '([0-9a-f]{32})'",source);assert len(ids)==1
config=json.loads((root/'config/pan_manual.local.json').read_text(encoding='utf-8'))
script=r'''
import hashlib,json,os
from pathlib import Path
config=CONFIG;app=APP
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==BOOT
fdt=hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest()
firmware=Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
state=Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()
vart=Path('/etc/vart.conf').read_text()
cid=Path('/sys/block/mmcblk1/device/cid').read_text().strip()
expected_vart='firmware: /lib/firmware/xilinx/'+app+'/'+app+'.xclbin\n'
checks={'architecture':os.uname().machine=='aarch64','root_uid':os.geteuid()==0,'board_identity':cid==CID,
 'boot':boot==config['boot_id'],'fdt':fdt==config['fdt_sha256'],
 'firmware':firmware==app+'.bit.bin','fpga_operating':state=='operating','vart':vart==expected_vart}
manifest=Path(config['release_manifest']);raw=manifest.read_bytes();release=json.loads(raw)
checks['release_manifest']=hashlib.sha256(raw).hexdigest()==config['release_manifest_sha256']
installed={}
for name,digest in release.get('runtime_files',{}).items():
 p=Path(name);installed[name]={'exists':p.is_file(),'sha256_matches':p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==digest}
payload={}
for name,digest in release.get('payload_files',{}).items():
 p=manifest.parent/name;payload[name]={'exists':p.is_file(),'sha256_matches':p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==digest}
print(json.dumps({'checks':checks,'expected':{'boot':config['boot_id'],'fdt_sha256':config['fdt_sha256'],
 'firmware':app+'.bit.bin','vart':expected_vart.strip()},
 'actual':{'boot':boot,'fdt_sha256':fdt,'firmware':firmware,'vart':vart.strip(),'fpga_state':state},
 'release':{'path':str(manifest),'status':release.get('status'),'app':release.get('app'),'boot_id':release.get('boot_id')},
 'installed_runtime_files':installed,'payload_files':payload,'configuration_changed':False,
 'fpga_reprogrammed':False,'driver_imported':False,'register_io':False,'motion_command_sent':False}))
'''.replace('CONFIG',repr(config)).replace('APP',repr(app)).replace('BOOT',repr(baseline['boot'])).replace('CID',repr(ids[0]))
data=json.loads(ssh('python3 -B -',script,timeout=25))
mapping={'boot':'BOOT_MISMATCH','fdt':'FDT_MISMATCH','firmware':'FPGA_FIRMWARE_MISMATCH','vart':'VART_MISMATCH'}
data['blockers']=[value for key,value in mapping.items() if not data['checks'][key]]
data['state']='PROTECTED_DISABLED' if data['blockers'] else 'PLATFORM_MATCHES_NO_MOTION_PERFORMED'
data['checked_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
save('motion_binding_audit.json',data)
print(json.dumps({'state':data['state'],'checks':data['checks'],'blockers':data['blockers'],
 'actual':data['actual'],'expected':data['expected'],
 'installed_payload_intact':all(r['sha256_matches'] for r in list(data['installed_runtime_files'].values())+list(data['payload_files'].values())),
 'register_io':False},ensure_ascii=True))
