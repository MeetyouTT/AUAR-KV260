#!/usr/bin/env python3
"""One UVC owner, a latest-frame detector worker and full-screen overlay.

CPU face demo only. There is no motion driver, MMIO, FPGA loading or SFace job.
"""
import argparse
from collections import deque
import hashlib
import json
import signal
import statistics
import sys
import threading
import time
import uuid
from pathlib import Path

import cv2
import numpy as np
from vision_core import FaceTracks, ControlPreview, display_observation
from motion_service import MotionService

MODEL_ROOT = Path('/home/root/aura-adaptation-20261006/identity')
BACKEND_SHA = 'ee34109e23423d99a4ea3ff75c2bf9d113329b1c8162cd02f30e7dfcfb6bfeaf'


def detector(model_root):
    backend = Path(__file__).with_name('face_compat_fast.py')
    if hashlib.sha256(backend.read_bytes()).hexdigest() != BACKEND_SHA:
        raise RuntimeError('Validated face backend hash mismatch')
    sys.path.insert(0, str(backend.parent))
    from face_compat_fast import YuNetCompat
    cv2.setNumThreads(2)
    return YuNetCompat(model_root/'models/yunet_2022mar.onnx', input_size=192)


def atomic_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, allow_nan=False))
    temporary.replace(path)


def orient_frame(image, mirror_horizontal=False):
    """Orient once before inference and display consume the shared frame."""
    return cv2.flip(image, 1) if mirror_horizontal else image


def preflight(model_root):
    fixture = np.arange(2*7*3, dtype=np.uint8).reshape(2,7,3)
    mirrored = orient_frame(fixture, True)
    assert np.array_equal(mirrored, fixture[:, ::-1, :])
    assert orient_frame(fixture) is fixture
    assert np.array_equal(orient_frame(mirrored, True), fixture)
    d = detector(model_root)
    image = cv2.imread(str(model_root/'reference/lena.jpg'))
    if image is None:
        raise RuntimeError('Fixed reference image unavailable')
    faces = d.detect(image)
    assert len(faces)==1
    assert len(d.detect(orient_frame(image, True)))==1
    assert len(d.detect(np.zeros((480,640,3),np.uint8)))==0
    tracker = FaceTracks('preflight')
    first = tracker.update(faces, 1, 1., 512, 512)
    second = tracker.update(faces, 2, 1.1, 512, 512)
    assert first['target_id'] is None and second['target_id']==1
    assert display_observation(second, 1.2)['target_visible']
    missing = tracker.update([], 3, 1.2, 512, 512)
    assert not display_observation(missing, 1.2)['target_visible']
    assert not display_observation(second, 1.5)['target_visible']
    control = ControlPreview()
    assert not control.update(missing,512,1.2)['valid']
    return {'passed': True, 'opencv': cv2.__version__, 'reference_faces': int(len(faces)),
            'blank_faces': 0, 'target_confirmation_passed': True,
            'loss_and_stale_checks_passed': True,
            'orientation_pixel_checks_passed': True, 'mirrored_reference_faces': 1,
            'camera_opened': False, 'motion_command_emitted': False}


def run(root, model_root, duration, motion_sim=False, mirror_horizontal=False):
    import gi
    gi.require_version('Gst', '1.0')
    gi.require_version('GstVideo', '1.0')
    from gi.repository import Gst, GstVideo
    from x11_window import Window
    Gst.init(None)
    root.mkdir(parents=True, exist_ok=True)
    epoch = uuid.uuid4().hex
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    stop = threading.Event()
    observation_path = Path('/run/aura-vision-observation')/(epoch+'.json')
    observation_path.parent.mkdir(parents=True, exist_ok=True)
    observation_lock = threading.Lock()
    lock = threading.Condition()
    latest = {'packet': None, 'snapshot': None, 'control': None, 'error': None,
              'capture_frames': 0, 'detected_frames': 0, 'display_frames': 0, 'rendered_frames': 0,
              'skipped_for_detection': 0, 'peak_faces': 0, 'confirmed_observations': 0,
              'lost_observations': 0, 'loss_after_tracking': 0, 'detector_ready': False}
    timings, ages = deque(maxlen=300), deque(maxlen=300)
    started = time.monotonic()
    motion = MotionService(boot, epoch) if motion_sim else None
    if motion:
        motion.resume_simulation(started)  # Explicit SIM-only launch flag.
    previous_motion_event = None
    motion_event_path = root/'motion-simulation.jsonl'
    capture = display = window = worker = None
    previous_event = None
    event_path = root/'events.jsonl'

    def record_motion(state, now):
        nonlocal previous_motion_event
        signature = (state['state'], state['reason'], state['control'].get('reason'),
                     state['simulated_submit_attempts'], state['controller_accepted_seq'])
        if signature != previous_motion_event:
            if motion_event_path.exists() and motion_event_path.stat().st_size > 1024*1024:
                motion_event_path.replace(root/'motion-simulation.previous.jsonl')
            with motion_event_path.open('a') as f:
                f.write(json.dumps({'boot_id':boot, 'epoch':epoch, 'recorded_time':now,
                                    'motion_simulation':state}, allow_nan=False)+'\n')
            previous_motion_event = signature

    def publish_observation(snapshot=None, error=None, stopped=False, inference_started=None, inference_completed=None):
        # Inference completion publishes to RAM; rendering never delays control data.
        with observation_lock:
            atomic_json(observation_path, {
                'boot_id':boot, 'epoch':epoch, 'mirror_horizontal':mirror_horizontal,
                'capture_size':[640,480], 'snapshot':snapshot,
                'publication_time':time.monotonic(),
                'inference_started':inference_started, 'inference_completed':inference_completed,
                'stopped':stopped or stop.is_set(), 'error':error,
                'scope':'VISION_OBSERVATION_ONLY', 'motion_command_emitted':False})
    publish_observation()

    def failure(error):
        with lock:
            latest['error'] = str(error)
            stop.set()
            lock.notify_all()
        publish_observation(error=str(error), stopped=True)

    def sample(sink):
        try:
            s = sink.emit('pull-sample')
            if s is None:
                return Gst.FlowReturn.EOS
            observed = time.monotonic()
            info = GstVideo.VideoInfo()
            assert info.from_caps(s.get_caps()), 'Invalid video caps'
            if (info.width, info.height)!=(640,480):
                raise RuntimeError('Unexpected capture dimensions')
            buffer = s.get_buffer()
            ok, mapping = buffer.map(Gst.MapFlags.READ)
            assert ok, 'Cannot map camera frame'
            try:
                image = np.ndarray((info.height,info.width,3),dtype=np.uint8,
                                   buffer=mapping.data, strides=(info.stride[0],3,1)).copy()
            finally:
                buffer.unmap(mapping)
            image = orient_frame(image, mirror_horizontal)
            image.setflags(write=False)
            with lock:
                latest['capture_frames'] += 1
                fid = latest['capture_frames']
                latest['packet'] = (fid, observed, image, int(buffer.pts))
                lock.notify_all()
            return Gst.FlowReturn.OK
        except Exception as exc:
            failure(exc)
            return Gst.FlowReturn.ERROR

    def inference():
        nonlocal previous_event
        try:
            d = detector(model_root)
            tracks, control = FaceTracks(epoch), ControlPreview()
            last_id = 0
            ever_tracked = False
            with lock:
                latest['detector_ready'] = True
            while not stop.is_set():
                with lock:
                    lock.wait_for(lambda: stop.is_set() or (latest['packet'] is not None and latest['packet'][0]>last_id), timeout=1.)
                    if stop.is_set():
                        break
                    packet = latest['packet']
                    if packet is None or packet[0]<=last_id:
                        continue
                fid, observed, image, _ = packet
                t0 = time.monotonic()
                faces = d.detect(image)
                done = time.monotonic()
                snapshot = tracks.update(faces,fid,observed,image.shape[1],image.shape[0])
                calculated = control.update(snapshot,image.shape[1],done)
                visible = display_observation(snapshot,done)
                if motion:
                    with motion.lock:
                        submitted = time.monotonic()
                        simulated = motion.observe(snapshot,image.shape[1],image.shape[0],submitted,boot)
                        record_motion(simulated,submitted)
                event = (visible['state'],snapshot['target_id'],len(faces))
                with lock:
                    timings.append((done-t0)*1000)
                    ages.append((done-observed)*1000)
                    latest['detected_frames'] += 1
                    latest['skipped_for_detection'] += max(0,fid-last_id-1)
                    latest['snapshot'],latest['control'] = snapshot,calculated
                    latest['peak_faces'] = max(latest['peak_faces'],len(faces))
                    if visible['target_visible']:
                        latest['confirmed_observations'] += 1
                        ever_tracked = True
                    else:
                        latest['lost_observations'] += 1
                        if ever_tracked:
                            latest['loss_after_tracking'] += 1
                publish_observation(snapshot, inference_started=t0, inference_completed=done)
                if event != previous_event:
                    if event_path.exists() and event_path.stat().st_size > 1024*1024:
                        event_path.replace(root/'events.previous.jsonl')
                    with event_path.open('a') as f:
                        f.write(json.dumps({'epoch':epoch,'frame_id':fid,'observed_time':observed,
                                            'completed_time':done,'state':visible['state'],
                                            'target_id':snapshot['target_id'],'face_count':len(faces),
                                            'control_preview':calculated})+'\n')
                    previous_event = event
                last_id = fid
        except Exception as exc:
            failure(exc)

    def status(now):
        with lock:
            result = {k:v for k,v in latest.items() if k not in ['packet','snapshot','control']}
            result['snapshot'] = latest['snapshot']
            result['control_preview'] = latest['control']
            packet, snapshot = latest['packet'], latest['snapshot']
            result['capture_age_ms'] = (now-packet[1])*1000 if packet else None
            result['observation'] = display_observation(snapshot,now) if snapshot else None
            result['detection_median_ms'] = statistics.median(timings) if timings else None
            result['observation_age_p95_ms'] = float(np.percentile(list(ages),95)) if ages else None
            result['motion_simulation'] = motion.status() if motion else None
        elapsed = now-started
        result.update(epoch=epoch, boot_id=boot, pid=__import__('os').getpid(),
                      elapsed_s=elapsed, capture_hz=result['capture_frames']/max(elapsed,.001),
                      detection_hz=result['detected_frames']/max(elapsed,.001),
                      device='/dev/video0', capture_size=[640,480], capture_format='YUY2',
                      detector_input_size=[192,192], detector_cpu_threads=2,
                      timestamp_kind='driver_dequeue', role='CPU_FACE_TRACKING_DEMO',
                      mirror_horizontal=mirror_horizontal,
                      coordinate_convention='MIRRORED_SELF_VIEW' if mirror_horizontal else 'CAMERA_NATIVE',
                      reference_x_px=320, physical_direction_calibration_valid=False,
                      control_observation_path=str(observation_path),
                      association='FACE_IOU_BASELINE', display_size=[window.width,window.height] if window else None,
                      window=int(window.handle) if window else None,
                      queue_capacity_frames=1, actuation_authorized=False,
                      motion_command_emitted=False, identity_recognition=False,
                      stopped=stop.is_set())
        return result

    def check_bus(pipeline):
        message = pipeline.get_bus().timed_pop_filtered(0,Gst.MessageType.ERROR|Gst.MessageType.EOS)
        if message is not None:
            if message.type == Gst.MessageType.ERROR:
                error, debug = message.parse_error()
                raise RuntimeError(str(error)+': '+str(debug))
            raise RuntimeError('Unexpected end of camera/display stream')

    def rendered(*_):
        with lock:
            latest['rendered_frames'] += 1

    signal.signal(signal.SIGTERM,lambda *_:stop.set())
    signal.signal(signal.SIGINT,lambda *_:stop.set())
    try:
        window = Window()
        capture = Gst.parse_launch('v4l2src device=/dev/video0 io-mode=mmap ! '
            'video/x-raw,format=YUY2,width=640,height=480,framerate=30/1 ! '
            'videoconvert ! video/x-raw,format=BGR ! '
            'appsink name=input emit-signals=true sync=false max-buffers=1 drop=true')
        capture.get_by_name('input').connect('new-sample',sample)
        display = Gst.parse_launch('appsrc name=output is-live=true format=time do-timestamp=true block=false '
            'max-bytes=921600 caps="video/x-raw,format=BGR,width=640,height=480,framerate=0/1,pixel-aspect-ratio=1/1" ! '
            'queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream ! '
            'videoconvert ! videoscale ! video/x-raw,width=%d,height=%d,pixel-aspect-ratio=1/1 ! '
            'identity name=render_counter signal-handoffs=true ! '
            'ximagesink name=screen sync=false force-aspect-ratio=true' % (window.width,window.height))
        display.get_by_name('render_counter').connect('handoff',rendered)
        GstVideo.VideoOverlay.set_window_handle(display.get_by_name('screen'),window.handle)
        for p in [display,capture]:
            assert p.set_state(Gst.State.PLAYING)!=Gst.StateChangeReturn.FAILURE, 'Cannot start video pipeline'
        worker = threading.Thread(target=inference,name='face-inference',daemon=True)
        worker.start()
        last_display, last_record, last_snapshot, last_wake = 0, 0., 0., 0.
        rendered_count, rendered_progress = 0, time.monotonic()
        while not stop.is_set():
            now = time.monotonic()
            if motion:
                with motion.lock:
                    checked = time.monotonic()
                    record_motion(motion.poll(checked),checked)
            if now-last_wake >= 30.:
                window.keep_awake()
                last_wake = now
            with lock:
                current_rendered = latest['rendered_frames']
            if current_rendered != rendered_count:
                rendered_count, rendered_progress = current_rendered, now
            if now-rendered_progress > 5.:
                raise RuntimeError('Display stopped accepting fresh frames')
            if duration and now-started >= duration:
                break
            check_bus(capture)
            check_bus(display)
            with lock:
                packet, snapshot, calculated = latest['packet'],latest['snapshot'],latest['control']
            if packet is not None and packet[0]>last_display:
                fid, observed, image, _ = packet
                if now-observed > 1.:
                    raise RuntimeError('Camera frames are stale')
                if display.get_by_name('output').get_property('current-level-bytes') >= image.nbytes:
                    time.sleep(.01)
                    continue
                painted = image.copy()
                view = display_observation(snapshot,now) if snapshot else {'state':'STARTING','fresh':False,'target_visible':False,'age_ms':0.}
                if snapshot and view['fresh']:
                    for track in snapshot['tracks']:
                        if not track['visible']:
                            continue
                        x,y,w,h = [int(v) for v in track['box']]
                        selected = track['track_id']==snapshot['target_id'] and view['target_visible']
                        color = (0,255,0) if selected else (0,200,255)
                        cv2.rectangle(painted,(x,y),(x+w,y+h),color,2)
                        cv2.putText(painted,'ID %d%s' % (track['track_id'],' TARGET' if selected else ''),
                                    (x,max(80,y-7)),cv2.FONT_HERSHEY_SIMPLEX,.55,color,2)
                        if selected:
                            cv2.circle(painted,(x+w//2,y+h//2),4,color,-1)
                header_height = 96 if motion else 72
                cv2.line(painted,(320,header_height+3),(320,479),(255,160,0),1)
                cv2.rectangle(painted,(0,0),(640,header_height),(0,0,0),-1)
                elapsed = max(now-started,.001)
                with lock:
                    counts = (latest['capture_frames'],latest['detected_frames'])
                target = snapshot['target_id'] if snapshot else None
                direction = calculated['direction'] if calculated and view['target_visible'] else view['state']
                error = calculated['filtered_error'] if calculated and view['target_visible'] else None
                lines = ['AURA FACE TRACKING | CPU | VISION PREVIEW'+(' | MIRROR' if mirror_horizontal else ''),
                         'Camera %.1f Hz  Detect %.1f Hz  Age %.0f ms' % (counts[0]/elapsed,counts[1]/elapsed,view['age_ms']),
                         'Target %s  %s  Error %s' % (target,direction,'%.3f'%error if error is not None else '--')]
                if motion:
                    m = motion.status()
                    lines.append('SIM %s  Command %+.2f deg  Seq %d | NO REAL OUTPUT' % (
                        m['state'],m['controller_accepted_mdeg']/1000,m['controller_accepted_seq']))
                for j,line in enumerate(lines):
                    cv2.putText(painted,line,(8,19+23*j),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
                buffer = Gst.Buffer.new_allocate(None,painted.nbytes,None)
                buffer.fill(0,painted.tobytes())
                flow = display.get_by_name('output').emit('push-buffer',buffer)
                if flow != Gst.FlowReturn.OK:
                    raise RuntimeError('Display rejected frame: '+str(flow))
                with lock:
                    latest['display_frames'] += 1
                last_display = fid
                if now-last_snapshot >= 2.:
                    ok, encoded = cv2.imencode('.jpg',painted,[cv2.IMWRITE_JPEG_QUALITY,75])
                    if ok:
                        temporary = root/'latest-preview.tmp'
                        temporary.write_bytes(encoded.tobytes())
                        temporary.replace(root/'latest-preview.jpg')
                    last_snapshot = now
            elif packet is None and now-started > 10.:
                raise RuntimeError('Camera produced no frames')
            elif packet is not None and now-packet[1] > 1.:
                raise RuntimeError('Camera stopped producing fresh frames')
            if now-last_record >= 1.:
                atomic_json(root/'status.json',status(now))
                last_record = now
            time.sleep(.01)
    except Exception as exc:
        failure(exc)
        raise
    finally:
        stop.set()
        with lock:
            lock.notify_all()
        if capture:
            capture.set_state(Gst.State.NULL)
        if display:
            display.set_state(Gst.State.NULL)
        if worker:
            worker.join(timeout=5.)
        if motion:
            with motion.lock:
                record_motion(motion.stop('PROCESS_EXIT'),time.monotonic())
        publish_observation(stopped=True)
        atomic_json(root/'status.json',status(time.monotonic()))
        if window:
            window.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--preflight',action='store_true')
    parser.add_argument('--model-root',type=Path,default=MODEL_ROOT)
    parser.add_argument('--run-root',type=Path,default=Path(__file__).resolve().parent/'run')
    parser.add_argument('--duration',type=float,default=0.)
    parser.add_argument('--motion-sim',action='store_true',help='In-memory controller only; no physical output')
    parser.add_argument('--mirror-horizontal', action='store_true', help='Mirror shared capture before detection and display')
    args = parser.parse_args()
    if args.preflight:
        print(json.dumps(preflight(args.model_root),indent=2))
    else:
        run(args.run_root,args.model_root,args.duration,args.motion_sim,args.mirror_horizontal)
