"""Read boot filesystem capacity and confirm the rejected install changed nothing."""
import hashlib,json,shutil
from pathlib import Path
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'usage':{},'boot_files':[],'files_modified':0}
for root in ['/boot','/home/root']:
 u=shutil.disk_usage(root);v['usage'][root]={'total':u.total,'used':u.used,'free':u.free}
for p in Path('/boot').iterdir():v['boot_files'].append({'name':p.name,'directory':p.is_dir(),'bytes':p.stat().st_size})
v['uenv_sha256']=hashlib.sha256(Path('/boot/uEnv.txt').read_bytes()).hexdigest()
v['candidate_backup_exists']=Path('/boot/aura-hdmi-preinit-20261021').exists()
v['candidate_boot_image_exists']=Path('/boot/Image-aura-hdmi-preinit-8bfafe019e09').exists()
v['staged_archive_sha256']=hashlib.sha256(Path('/home/root/aura-hdmi-preinit-20261021/d977bdda5e7c9877/Image.gz').read_bytes()).hexdigest()
print(json.dumps(v),flush=True)
