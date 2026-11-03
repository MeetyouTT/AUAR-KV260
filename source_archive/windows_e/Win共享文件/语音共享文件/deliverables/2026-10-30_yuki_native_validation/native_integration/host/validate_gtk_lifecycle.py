"""Untimed real GTK/EGL lifecycle regression, no app/jobs/audio/network."""
from pathlib import Path
from types import SimpleNamespace as S
import json,os,subprocess,sys,time
phase=Path('/home/root/aura-yuki-validation-20261030/native_integration')
sys.path.insert(0,str(phase/'host'))
from native_yuki import LocalPortrait,create_gl_area
pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
for value in Path('/proc',pid,'environ').read_bytes().split(b'\0'):
    key,sep,data=value.partition(b'=')
    if sep and key in (b'DISPLAY',b'XAUTHORITY'):os.environ[key.decode()]=os.fsdecode(data)
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib
assert Gtk.init_check([])[0]
assert json.loads((phase/'results/precision-validation-result.json').read_text())['status']=='PASS'
assets=phase/'runtime_assets';output=S(active=False,ready=False,paused=False)
box=LocalPortrait(output);core=S(talk_gen=1,emotion='neutral',fsm=S(state=S(label='IDLE')))
area=create_gl_area(dict(library=str(phase/'build_host/libaura_yuki.so'),model=str(assets/'model.runtime.json'),
  resx=str(assets/'yuk_0.ems.resx.json'),resource_root=str(assets),seed=1),box)
window=Gtk.Window();window.set_decorated(False);window.set_skip_taskbar_hint(True);window.set_skip_pager_hint(True)
window.set_accept_focus(False);window.set_opacity(0);window.move(-9000,-9000)
area.set_size_request(423,438);window.add(area)
checks={};state={'began':None,'step':0};errors=[];setup=time.monotonic()
def frames():return box.latest_stats.get('frames',0)
def poll():
    try:
        now=time.monotonic()
        if state['began'] is None:
            if not box.ready:
                if now-setup>20:raise RuntimeError('Lifecycle context startup timed out')
                return True
            state['began']=now
        elapsed=now-state['began']
        box.offer(core,elapsed,0,0,0,'none')
        if elapsed>=2 and state['step']==0:
            state['hidden_frames']=frames();area.hide();state['step']=1
            checks['unmap_cancels_source']=area.frame_source is None
        if elapsed>=3 and state['step']==1:
            checks['hidden_frames_stopped']=frames()==state['hidden_frames']
            area.show();state['step']=2
        if elapsed>=4 and state['step']==2:
            checks['map_resumes_same_instance']=frames()>state['hidden_frames']+8
            box.set_fps(12);state['rate_frames']=frames();state['step']=3
        if elapsed>=5 and state['step']==3:
            checks['rate_change_applied']=8<=frames()-state['rate_frames']<=16
            box.set_enabled(False);area.hide();state['disabled_frames']=frames();state['step']=4
        if elapsed>=6 and state['step']==4:
            checks['disabled_frames_stopped']=frames()==state['disabled_frames'] and area.frame_source is None
            box.set_enabled(True);area.show();state['step']=5
        if elapsed>=7 and state['step']==5:
            checks['reenable_resumes']=frames()>state['disabled_frames']+6
            area.failed(RuntimeError('injected isolated lifecycle failure'))
            checks['failure_releases_native_and_timer']=area.native is None and area.egl is None and area.frame_source is None
            checks['failure_selects_local_fallback']=not box.ready and box.status()['mode']=='local'
            state['step']=6
        if elapsed>=8:
            checks['failure_not_restarted']=area.native is None and area.frame_source is None
            Gtk.main_quit();return False
        return True
    except Exception as error:errors.append(str(error));Gtk.main_quit();return False
window.show_all();GLib.timeout_add(20,poll)
try:Gtk.main()
finally:window.destroy()
checks['destroy_releases_all']=area.native is None and area.egl is None and area.frame_source is None
report=dict(status='PASS' if len(checks)==10 and all(checks.values()) and not errors else 'FAIL',checks=checks,errors=errors,
  scope='synthetic mailbox; mapped transparent non-focusing window; private EGL; untimed lifecycle only',production_deployed=False)
(phase/'results/gtk-lifecycle.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
assert report['status']=='PASS'
