"""Show a bounded static X11 window; preserve display configuration and services."""
import hashlib, json, os, re, subprocess, time, urllib.request
from pathlib import Path

BOOT='975f931a-927b-4a06-b784-ebda8463177f'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
for name,sha in {'/boot/uEnv.txt':'d120b2f78e40ec690fcda92f5c0791a93d587cf75d399695301005c45800d369','/etc/X11/xorg.conf':'64457c25a844ef95cd4ae62bacba80b0cbec5ae1a54efdc15e3ec02775c0555a'}.items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha

def cmd(args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
    return {'rc':p.returncode,'text':p.stdout[-6000:]}

def gui():
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with op.open('http://127.0.0.1:8783/api/state',timeout=2) as r:s=json.load(r)
    return {k:s.get(k) for k in ['phase','playing','ui_page','error','avatar_display']}

def sample():
    raw=Path('/sys/class/drm/card0-DP-1/edid').read_bytes()
    return {'units':cmd(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service','-p','Id','-p','MainPID','-p','ActiveState','-p','NRestarts']), 'edid_bytes':len(raw),'edid_sha256':hashlib.sha256(raw).hexdigest(),'gui':gui()}

before=sample()
assert before['gui']['phase']=='IDLE' and not before['gui']['playing'],'Application busy'
assert before['units']['text'].count('ActiveState=active')==3
root=Path('/run/aura-hdmi-static-test-20261021')/BOOT
root.mkdir(parents=True,exist_ok=False)
pattern='''import gi,json,time
from pathlib import Path
gi.require_version('Gtk','3.0')
gi.require_version('Gdk','3.0')
from gi.repository import Gtk,Gdk,GLib
ROOT=Path(__file__).parent
start=time.monotonic()
state={'pattern':'static_gray','draw_calls':0,'samples':[],'completed':False}
win=Gtk.Window()
win.set_decorated(False)
win.set_keep_above(True)
win.set_skip_taskbar_hint(True)
win.set_accept_focus(False)
win.set_focus_on_map(False)
win.set_default_size(1024,600)
win.fullscreen()
win.set_app_paintable(True)
def draw(widget,cr):
 state['draw_calls']+=1
 cr.set_source_rgb(.5,.5,.5);cr.paint()
 cr.set_source_rgb(1,1,1);cr.select_font_face('Sans');cr.set_font_size(26)
 cr.move_to(260,295);cr.show_text('STATIC DISPLAY TEST - 20 s')
 return False
win.connect('draw',draw)
def save():
 (ROOT/'pattern-state.json').write_text(json.dumps(state)+'\\n')
def measure():
 values=[]
 for x,y in [(100,100),(924,100),(512,500)]:
  p=Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),x,y,1,1)
  values.append(list(p.get_pixels()[:3]) if p else None)
 state['samples'].append({'elapsed':round(time.monotonic()-start,3),'window_size':list(win.get_size()),'pixels':values})
 save()
 return len(state['samples'])<15
def finish():
 state['completed']=True;state['elapsed_seconds']=round(time.monotonic()-start,3);save()
 win.destroy()
 return False
win.connect('destroy',lambda *_:Gtk.main_quit())
win.show_all()
GLib.timeout_add(1000,measure)
GLib.timeout_add(20000,finish)
Gtk.main()
'''
(root/'pattern.py').write_text(pattern)
unit='aura-hdmi-static-test-'+BOOT[:8]
launch=cmd(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=30','--setenv=DISPLAY=:0','/usr/bin/python3','-B',str(root/'pattern.py')])
assert launch['rc']==0,launch
deadline=time.monotonic()+29
while time.monotonic()<deadline:
    p=root/'pattern-state.json'
    if p.exists():
        try:state=json.loads(p.read_text())
        except ValueError:state={}
        if state.get('completed'):break
    time.sleep(.5)
else:state={}
unit_status=cmd(['systemctl','show',unit+'.service','-p','ActiveState','-p','SubState','-p','ExecMainStatus'])
if 'ActiveState=active' in unit_status['text']:
    cmd(['systemctl','stop',unit+'.service'])
v={'boot_id':BOOT,'before':before,'after':sample(),'pattern':state,'launch':launch,'unit_final':unit_status,
   'mode_changes':0,'production_service_restarts':0,'movement_commands_sent':0,'physical_pattern_result':'awaiting_user'}
v['static_source_pixels_verified']=bool(state.get('completed') and len(state.get('samples',[]))==15 and all(s['window_size']==[1024,600] and all(p and all(abs(c-128)<12 for c in p) for p in s['pixels']) for s in state['samples']))
v['display_after']=cmd(['env','DISPLAY=:0','xrandr','--current'])
kernel=subprocess.check_output(['dmesg'],text=True)
v['kernel_errors']=[s for s in kernel.splitlines() if re.search(r'underflow|training.*(?:fail|error)|aux.*(?:fail|error)|usb.*(?:disconnect|reset|over.current)',s,re.I)][-25:]
(root/'result.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(v),flush=True)
