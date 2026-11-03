"""Audit staged joint firmware and files; no MMIO or application switching."""
import hashlib,json
from pathlib import Path
root=Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
firmware=Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
report={'status':'READ_ONLY_JOINT_PLATFORM_READINESS','boot_id':boot,'current_firmware':firmware,
 'joint_runtime_present':root.is_dir(),'registers_opened':False,'pwm_sent':False,'fpga_changed':False,
 'driver_firmware_gate_satisfied':firmware=='aura-visual-servo-b4096-v1.bit.bin'}
p=root/'payload_manifest.json'
if p.exists():
 manifest=json.loads(p.read_text());groups={}
 for group in ['payload_files','runtime_files']:
  missing=[];mismatch=[];count=0
  for name,digest in manifest.get(group,{}).items():
   path=root/name if group=='payload_files' else Path('/'+name)
   if not path.is_file():missing.append(name);continue
   count+=1
   if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:mismatch.append(name)
  groups[group]={'checked':count,'missing':missing,'mismatches':mismatch,'all_match':not missing and not mismatch}
 report['manifest_verification']=groups
 snapshot=root/'baseline-snapshot.json'
 if snapshot.exists():
  snapshot=json.loads(snapshot.read_text());files=snapshot.get('firmware_hashes',{})
  report['official_firmware_files_match_saved_baseline']=all(Path(name).is_file() and hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest for name,digest in files.items()) if files else None
  report['vart_configuration_matches_saved_baseline']=Path('/etc/vart.conf').read_text()==snapshot.get('vart_conf')
for name in ['aura-visual-servo-b4096-v1.bit.bin','aura-visual-servo-b4096-v1.xclbin','aura-visual-servo-b4096-v1.dtbo']:
 path=Path('/lib/firmware/xilinx/aura-visual-servo-b4096-v1')/name
 report[name]={'exists':path.is_file(),'bytes':path.stat().st_size if path.is_file() else None}
p=Path('/sys/module/zocl/refcnt')
report['zocl_refcnt']=p.read_text().strip() if p.exists() else None
print(json.dumps(report),flush=True)
