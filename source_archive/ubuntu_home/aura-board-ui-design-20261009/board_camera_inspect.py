"""Read-only camera ownership, format and UI failure evidence; no capture."""
import hashlib, json, os, subprocess, time
from pathlib import Path

def run(args):
    try:
        r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
        return {'rc':r.returncode,'output':r.stdout[-14000:]}
    except Exception as e:return {'error':str(e)}

root=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
out={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
     'monotonic':time.monotonic(),'memory':Path('/proc/meminfo').read_text(),
     'video':[],'owners':[],'related_processes':[]}
for node in sorted(Path('/sys/class/video4linux').glob('video*')):
    device='/dev/'+node.name
    item={'device':device,'sys_path':str(node.resolve()),'name':(node/'name').read_text().strip()}
    item['formats']=run(['v4l2-ctl','-d',device,'--list-formats-ext'])
    item['info']=run(['v4l2-ctl','-d',device,'--all'])
    out['video'].append(item)
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        argv=(p/'cmdline').read_bytes().decode(errors='replace').replace(chr(0),' ').strip()
        fds=[]
        for fd in (p/'fd').iterdir():
            try:
                value=os.readlink(str(fd))
                if value.startswith('/dev/video'):fds.append(value)
            except OSError:pass
        if fds:out['owners'].append({'pid':int(p.name),'argv':argv,'devices':fds})
        if any(x in argv for x in ('realtime_vision.py','board_avatar_gtk.py','launcher.py','Xorg','dfx-mgrd')):
            stat=(p/'status').read_text().splitlines()
            out['related_processes'].append({'pid':int(p.name),'argv':argv,
                'memory':[x for x in stat if x.startswith(('VmRSS:','VmHWM:','Threads:'))]})
    except OSError:pass
out['ui_journal']=run(['journalctl','-u','aura-avatar-ui.service','-n','60','--no-pager'])
kernel=run(['dmesg'])
out['kernel_relevant']=[x for x in kernel.get('output','').splitlines() if any(k in x.lower() for k in ('oom','killed process','out of memory','segfault','uvc','video0'))][-45:]
out['vision_releases']=[str(x) for x in Path('/home/root/aura-realtime-vision-20261007/releases').glob('*')]
out['socket_listeners']=run(['ss','-lntp'])
info=json.loads((root/'launch.json').read_text())
out['launch']=info
setup=Path(info['session'])/'setup.json'
out['display_setup']=json.loads(setup.read_text()) if setup.exists() else None
out['protected']={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in (
    '/lib/systemd/system/xserver-nodm.service','/etc/default/xserver-nodm',
    '/etc/modules-load.d/aura-touch.conf','/lib/modules/5.15.36-xilinx-v2022.2/extra/aura/hid-multitouch.ko')}
latest=Path(info['evidence'])/'latest_verification.json'
out['latest_report']=json.loads(latest.read_text()) if latest.exists() else None
out['settings']={p.name:json.loads(p.read_text()) for p in (root/'avatar_user_settings.json',root/'avatar_service_settings.json') if p.exists()}
units={}
for name in ('aura-avatar-ui.service','aura-camera-ui.service'):
    path=Path('/etc/systemd/system')/name
    if path.exists():units[name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'state':run(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','SubState','-p','NRestarts','-p','UnitFileState'])}
out['units']=units
stage=root/'ui-design-update-49e441bea05c3d3f'
if (stage/'APPLIED.json').exists():
    applied=json.loads((stage/'APPLIED.json').read_text());out['applied']=applied
    out['runtime_hashes']={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in applied['runtime_files']}
    out['native_test_log']=(stage/'native-tests.log').read_text()
print(json.dumps(out,ensure_ascii=False))
