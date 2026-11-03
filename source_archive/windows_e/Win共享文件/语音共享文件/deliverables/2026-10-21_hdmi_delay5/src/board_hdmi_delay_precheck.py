"""Read-only checks before staging the DP wake delay boot argument."""
import gzip,hashlib,json,os,subprocess,zlib,struct
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(a):
 p=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
 return {'rc':p.returncode,'text':p.stdout}
base=Path('/home/root/aura-speech-motion-20261021/922dab49a74f/startup')
b=Path('/boot/boot.scr').read_bytes();h=bytearray(b[:64]);f=struct.unpack('>7I4B32s',h);h[4:8]=b'\0'*4
assert f[0]==0x27051956 and len(b)==64+f[3]
assert zlib.crc32(h)&0xffffffff==f[1] and zlib.crc32(b[64:])&0xffffffff==f[6]
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'cid':Path('/sys/block/mmcblk1/device/cid').read_text().strip(),'cmdline':Path('/proc/cmdline').read_text().strip(),'dt_bootargs':Path('/proc/device-tree/chosen/bootargs').read_bytes().rstrip(b'\0').decode(),'boot_script_sha256':sha('/boot/boot.scr'),'boot_script_crc_valid':True,'uenv_exists':Path('/boot/uEnv.txt').exists(),'delay_ms':Path('/sys/module/zynqmp_dpsub/parameters/power_on_delay_ms').read_text().strip(),'kernel':os.uname().release,'files_modified':0,'display_commands_sent':0,'movement_commands_sent':0}
v['boot_mount']=[s for s in Path('/proc/mounts').read_text().splitlines() if s.split()[1]=='/boot']
v['config_hashes']={str(p):sha(p) for p in [base/'launcher.py',base/'config.json',Path('/etc/X11/xorg.conf')]}
v['kernel_config']=[s for s in gzip.decompress(Path('/proc/config.gz').read_bytes()).decode().splitlines() if s.startswith(('CONFIG_DRM_ZYNQMP_DPSUB=','CONFIG_CMDLINE','CONFIG_BOOT_CONFIG'))]
v['units']=run(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts','-p','TimeoutStartUSec'])
v['launcher_timeouts']=[s.strip() for s in (base/'launcher.py').read_text().splitlines() if 'timeout' in s or 'deadline' in s]
v['edid_bytes']=len(Path('/sys/class/drm/card0-DP-1/edid').read_bytes())
print(json.dumps(v),flush=True)
