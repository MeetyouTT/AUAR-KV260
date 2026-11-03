"""Export only build metadata/config and display topology; no bus probing."""
import base64,gzip,hashlib,json,os,shutil
from pathlib import Path
def sh(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'version':Path('/proc/version').read_text().strip(),'kernel':os.uname().release,'boot_image_sha256':sh('/boot/Image'),'files_modified':0,'display_commands_sent':0,'movement_commands_sent':0}
raw=Path('/proc/config.gz').read_bytes()
v['running_config_sha256']=hashlib.sha256(gzip.decompress(raw)).hexdigest()
v['tools']={x:shutil.which(x) for x in ['i2ctransfer','i2cget','modinfo','dtc']}
v['display_device']=str(Path('/sys/class/drm/card0/device').resolve())
v['i2c_adapters']={p.name:(p/'name').read_text().strip() for p in Path('/sys/class/i2c-adapter').glob('i2c-*')}
v['dt_compatible']=Path('/sys/firmware/devicetree/base/compatible').read_bytes().rstrip(b'\0').decode().split('\0')
v['dt_model']=Path('/sys/firmware/devicetree/base/model').read_bytes().rstrip(b'\0').decode()
v['driver_parameters']={p.name:p.read_text().strip() for p in Path('/sys/module/zynqmp_dpsub/parameters').glob('*')}
v['artifacts']={'running.config.gz':{'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}}
print(json.dumps(v),flush=True)
