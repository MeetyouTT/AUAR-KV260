"""Read framebuffer and active Xorg entry before fixing initial resolution."""
import base64, gzip, hashlib, json, re, subprocess
from pathlib import Path

def run(args):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=6)
    return {'rc':p.returncode, 'text':p.stdout[-12000:]}

v = {'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
     'cmdline':Path('/proc/cmdline').read_text().strip(), 'files_modified':0}
v['framebuffers'] = {}
for p in Path('/sys/class/graphics').glob('fb*'):
    v['framebuffers'][p.name] = {k:(p/k).read_text().strip() for k in ['name','modes','mode','virtual_size','bits_per_pixel'] if (p/k).exists()}
p = Path('/sys/module/drm_kms_helper/parameters/fbdev_emulation')
v['fbdev_emulation'] = p.read_text().strip() if p.exists() else None
config = gzip.decompress(Path('/proc/config.gz').read_bytes()).decode()
v['config'] = [line for line in config.splitlines() if re.match(r'(?:CONFIG_(?:DRM_FBDEV_EMULATION|FRAMEBUFFER_CONSOLE|DRM_KMS_HELPER|DRM_ZYNQMP_DPSUB|FB)=|# CONFIG_FRAMEBUFFER_CONSOLE)', line)]
v['fb_device_users'] = []
for p in Path('/proc').glob('[0-9]*/fd/*'):
    try:
        if str(p.resolve()).startswith('/dev/fb'):
            v['fb_device_users'].append({'pid':int(p.parts[2]),'fd':p.name})
    except OSError:
        pass
v['units'] = run(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts','-p','ExecStart'])
pid = int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip())
argv = Path('/proc/%d/cmdline'%pid).read_bytes().decode().split('\0')
cfg = Path(argv[argv.index('--config')+1]); launcher = cfg.with_name('launcher.py')
v['protected'] = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [cfg,launcher,Path('/boot/uEnv.txt'),Path('/etc/X11/xorg.conf')]}
v['xorg_setup'] = [s for s in Path('/var/log/Xorg.0.log').read_text().splitlines() if re.search(r'Using config|Monitor|initial mode|DefaultDepth|depth|1024x768',s,re.I)]
kernel = subprocess.check_output(['dmesg'],text=True)
v['early_display'] = [s for s in kernel.splitlines() if re.search(r'fb0|Console:|frame buffer|drm|zynqmp-display',s,re.I)][:35]
v['artifacts'] = {}
for name, p in [('xorg-before.conf',Path('/etc/X11/xorg.conf')),('xserver-startup.txt',Path('/etc/xserver-nodm/Xserver'))]:
    data=p.read_bytes();v['artifacts'][name]={'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
print(json.dumps(v),flush=True)
