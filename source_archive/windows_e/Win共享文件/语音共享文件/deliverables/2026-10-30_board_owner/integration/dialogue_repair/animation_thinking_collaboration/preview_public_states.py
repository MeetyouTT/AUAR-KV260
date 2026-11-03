"""One isolated GTK/EGL owner; only public character frames and fake envelope.

The main coordinator stops production normally and provides DISPLAY/XAUTHORITY.
This script never opens audio/camera/network/business stores, reads live text,
starts/stops services, or captures a desktop. Capture is renderer.capture only.
"""
import argparse
from collections import deque
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
from types import ModuleType, SimpleNamespace as S

HERE=Path(__file__).resolve().parent
PHASES=(('IDLE',2.),('ASR_WAIT',2.),('THINKING',4.),('BUFFER_READY',2.),
        ('ANSWER',4.),('PAUSED',2.),('ANSWER_RESUMED',3.),('CANCELLED',2.),('IDLE_RETURN',3.))
CAPTURE_PHASES=frozenset(('THINKING','BUFFER_READY','ANSWER','PAUSED','CANCELLED','IDLE_RETURN'))
TOTAL_SECONDS=sum(seconds for _,seconds in PHASES)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def plan(elapsed):
    cursor=0.
    for name,seconds in PHASES:
        if elapsed<cursor+seconds:
            local=max(0.,elapsed-cursor)
            answering=name in ('ANSWER','ANSWER_RESUMED')
            paused=name=='PAUSED'
            active=answering or paused or name=='BUFFER_READY'
            audio_clock=local if name=='ANSWER' else 4.+local if name=='ANSWER_RESUMED' else 4. if paused else 0.
            return dict(phase=name,phase_elapsed=local,
                fsm='SPEAKING_NEUTRAL' if active else 'THINKING' if name=='THINKING' else 'IDLE',
                active=active,paused=paused,ready=active,audible=answering or paused,
                track='answer' if answering or paused else None,
                audio_clock=audio_clock,waiting=name in ('ASR_WAIT','THINKING','BUFFER_READY'),
                gain=.85 if answering else 0.,
                level=.12+.78*(.5+.5*math.sin(audio_clock*math.tau*1.3)) if answering else 0.,
                expected_eye=0. if answering else 10. if name in ('ASR_WAIT','THINKING','BUFFER_READY','PAUSED') else None,
                expected_mouth_moving=answering)
        cursor+=seconds
    return None


def check_files(runtime):
    spec=json.loads((HERE/'PREVIEW_SPEC.json').read_text(encoding='utf-8'))
    if sha(Path(__file__).resolve())!=spec['script_sha256']:
        raise ValueError('preview_script_pin_mismatch')
    overlay=HERE/'paired_overlay/aura'
    for relative,expected in spec['overlay_pins'].items():
        path=overlay/relative
        if not path.resolve(strict=True).is_relative_to(overlay.resolve(strict=True)) or sha(path)!=expected:
            raise ValueError('preview_overlay_pin_mismatch')
    for relative,expected in spec['public_runtime_pins'].items():
        path=runtime/relative
        if not path.resolve(strict=True).is_relative_to(runtime) or sha(path)!=expected:
            raise ValueError('public_character_asset_pin_mismatch')
    selection=json.loads((overlay/'config/yuki_pair.formal.json').read_text(encoding='utf-8'))
    if sha(overlay/'config/yuki_pair.formal.json')!=spec['selection_sha256']:
        raise ValueError('preview_pair_selection_mismatch')
    return spec,selection,overlay


def unit_stopped(unit):
    # Read a numeric service property only. Never inspect /api/state, command
    # line bodies, process environments, databases or live conversation files.
    result=subprocess.run(['systemctl','show',unit,'-p','MainPID','--value'],
                          capture_output=True,text=True,check=True,timeout=3)
    return result.stdout.strip()=='0'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runtime',type=Path,required=True,help='Existing public runtime/aura directory')
    parser.add_argument('--evidence',type=Path,default=HERE/'preview_evidence')
    parser.add_argument('--owner-unit',default='aura-avatar-ui.service')
    parser.add_argument('--capture-character',action='store_true')
    parser.add_argument('--validate-only',action='store_true')
    args=parser.parse_args()
    runtime=args.runtime.resolve(strict=True)
    spec,selection,overlay=check_files(runtime)
    if args.validate_only:
        print(json.dumps(dict(status='PUBLIC_INPUT_PINS_VALID',selection_sha256=spec['selection_sha256'],
            public_runtime_files=len(spec['public_runtime_pins']),overlay_files=len(spec['overlay_pins']),
            gtk_or_egl_opened=False,audio_or_camera_opened=False,live_state_or_private_data_read=False)))
        return
    if platform.system()!='Linux' or not os.environ.get('DISPLAY'):
        raise ValueError('coordinator_linux_display_environment_required')
    if not unit_stopped(args.owner_unit):
        raise ValueError('production_display_owner_still_running')
    # Prevent two copies of this preview. Production itself is guarded/stopped
    # by the coordinator; this script cannot obtain or change that service.
    import fcntl
    lock=(HERE/'public_preview.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    evidence=args.evidence.resolve()
    if not evidence.is_relative_to(HERE):
        raise ValueError('preview_evidence_must_stay_inside_its_stage')
    evidence.mkdir(exist_ok=False)
    sys.dont_write_bytecode=True
    # Import only the paired display adapters and the unchanged public EGL
    # module. No production entry/factory/configuration is imported or started.
    package=ModuleType('tools');package.__path__=[str(overlay/'tools'),str(runtime/'tools')]
    sys.modules['tools']=package
    from tools.formal_native_yuki import StrictLocalPortrait,create_gl_area
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk,GLib
    if not Gtk.init_check([])[0]:
        raise ValueError('preview_gtk_display_unavailable')

    class PublicOutput:
        def __init__(self):
            self.active=self.paused=False;self.duration=7.;self.snapshot={};self.read_calls=0
        def read(self):
            self.read_calls+=1
            return dict(self.snapshot)
        def apply(self,p):
            self.active=p['active'];self.paused=p['paused']
            self.snapshot=dict(ready=p['ready'],audible=p['audible'],track=p['track'],
                clock=p['audio_clock'],answer_clock=p['audio_clock'],done=False,error='')

    output=PublicOutput()
    core=S(talk_gen=1,emotion='neutral',fsm=S(state=S(label='IDLE')))
    mailbox=StrictLocalPortrait(output,clock=time.monotonic)
    errors=[];closing=False

    class PublicPair:
        # Only satisfy the display readiness callback. No runtime, persona,
        # admission, jobs, settings, store or business object is constructed.
        def observe_native_frame(self,stats):
            with mailbox.lock:mailbox._drawn=True
        def fail(self,code):
            if not closing:
                errors.append('NATIVE_RENDERER_FAILED' if code!='native_unrealized' else 'UNEXPECTED_UNREALIZE')
                GLib.idle_add(Gtk.main_quit)

    config=dict(selection['native_config'])
    config['library']=str(overlay/config['library'])
    for name in ('model','resx','resource_root'):
        config[name]=str(runtime/config[name])
    window=Gtk.Window()
    window.set_title('雪妃 · 公开动画预览')
    window.set_decorated(False);window.set_accept_focus(False)
    window.set_default_size(423,516);window.set_position(Gtk.WindowPosition.CENTER)
    area=create_gl_area(config,mailbox,PublicPair())
    area.set_size_request(423,516);window.add(area)
    original_observer=area.frame_observer
    rows=deque(maxlen=640);controls={};captures={};started=None;previous_phase=None;cancel_applied=False

    def quit_preview(code=None):
        if code:errors.append(code)
        Gtk.main_quit()
        return False

    def observe(stats):
        nonlocal started,previous_phase,cancel_applied
        try:
            original_observer(stats)
            now=time.monotonic()
            if started is None:started=now
            elapsed=now-started
            consumed=controls.pop(int(stats['sequence']),None)
            if consumed is not None:
                row=dict(phase=consumed['phase'],phase_elapsed=consumed['phase_elapsed'],at=elapsed,
                    expected_eye=consumed['expected_eye'],expected_mouth_moving=consumed['expected_mouth_moving'],
                    eye=stats['eye'],mouth=stats['mouth'],owner=stats['owner'],sequence=stats['sequence'],
                    audio_sample=stats['audio_sample'],paint_at=stats['paint_at'],
                    evaluate_ms=stats['evaluate_ms'],submit_ms=stats['submit_ms'],
                    stale_frames=stats['stale_frames'],rejected_controls=stats['rejected_controls'])
                rows.append(row)
                if (args.capture_character and row['phase'] in CAPTURE_PHASES
                    and row['phase'] not in captures and row['phase_elapsed']>=.6):
                    width=area.get_allocated_width()*area.get_scale_factor()
                    height=area.get_allocated_height()*area.get_scale_factor()
                    if (width,height)!=(423,516):
                        raise ValueError('unexpected_preview_capture_dimensions')
                    # Native framebuffer contains this character canvas only;
                    # never an OS screenshot, desktop or camera/UI thumbnail.
                    image=evidence/(row['phase'].lower()+'.png')
                    area.egl.current();area.native.capture(image,423,516)
                    captures[row['phase']]=dict(path=image.name,width=423,height=516,
                        sha256=sha(image),eye=row['eye'],mouth=row['mouth'],sequence=row['sequence'])
            p=plan(elapsed)
            if p is None:
                quit_preview();return
            if p['phase']=='CANCELLED' and not cancel_applied:
                mailbox.invalidate();core.talk_gen+=1;cancel_applied=True
            output.apply(p);core.fsm.state.label=p['fsm']
            mailbox.offer(core,elapsed,p['gain'],p['level'],round(p['audio_clock']*24000),
                          p['track'] or 'none',waiting_for_answer=p['waiting'])
            controls[mailbox.sequence]=p
            while len(controls)>32:controls.pop(next(iter(controls)))
            previous_phase=p['phase']
        except Exception:
            quit_preview('PREVIEW_FRAME_OR_CAPTURE_FAILED')

    area.frame_observer=observe
    window.connect('delete-event',lambda *_:quit_preview('EARLY_USER_CLOSE'))
    signal.signal(signal.SIGTERM,lambda *_:GLib.idle_add(quit_preview,'OWNER_TERMINATED'))
    signal.signal(signal.SIGINT,lambda *_:GLib.idle_add(quit_preview,'OWNER_INTERRUPTED'))
    # One coarse deadline; controls are offered by the existing native frame
    # observer, never by a second render loop or a high-frequency poll timer.
    watchdog=GLib.timeout_add_seconds(60,lambda:quit_preview('PREVIEW_DEADLINE'))
    unit_after=False
    try:
        window.show_all();Gtk.main()
    finally:
        closing=True
        GLib.source_remove(watchdog)
        window.destroy()
        mailbox.close()
        unit_after=unit_stopped(args.owner_unit)
        fcntl.flock(lock,fcntl.LOCK_UN);lock.close()

    stable=[row for row in rows if row['phase_elapsed']>=.25]
    counts={name:sum(row['phase']==name for row in stable) for name,_ in PHASES}
    answers=[row['mouth'] for row in stable if row['expected_mouth_moving']]
    checks=dict(all_phases_observed=all(count>=8 for count in counts.values()),
        requested_eye_policy_holds=all(abs(row['eye']-row['expected_eye'])<.00002
            for row in stable if row['expected_eye'] is not None),
        non_answer_mouth_closed=all(abs(row['mouth'])<.00002 for row in stable if not row['expected_mouth_moving']),
        answer_mouth_follows_public_envelope=bool(answers and max(answers)>.1 and max(answers)-min(answers)>.1),
        captures_complete=not args.capture_character or CAPTURE_PHASES<=set(captures),
        production_display_owner_still_stopped=unit_after,
        no_native_controls_rejected=all(row['rejected_controls']==0 for row in rows))
    passing=not errors and all(checks.values())
    paints=[row['paint_at'] for row in rows]
    report=dict(schema='aura.animation-thinking-public-preview.v1',
        status='NUMERIC_PASS_IMAGES_REQUIRE_REVIEW' if passing else 'FAIL',
        selection_sha256=spec['selection_sha256'],overlay_pins=spec['overlay_pins'],
        checks=checks,phase_stable_frames=counts,captures=captures,errors=errors,
        frames=len(rows),native_target_fps=16,
        native_swap_callback_fps=(len(paints)-1)/(paints[-1]-paints[0]) if len(paints)>1 else None,
        frame_measurement='native swap submission callbacks; physical scanout not measured',
        source='public simulated output states and numerical envelope; no PCM or real sink',
        public_output_read_calls=output.read_calls,read_ipc_operations=0,
        microphone_opened=False,audio_device_opened=False,camera_opened=False,
        network_or_model_calls=0,live_state_or_private_data_read=False,
        capture_scope='renderer framebuffer 423x516 character canvas only',
        physical_fps_measured=False,strict_16fps_acceptance_passed=False,
        visual_preview_passed=False,production_installed=False)
    save(evidence/'preview_result.json',report)
    save(evidence/'numeric_frames.json',list(rows))
    print(json.dumps(report,ensure_ascii=False),flush=True)
    if not passing:raise SystemExit(1)


if __name__=='__main__':
    main()
