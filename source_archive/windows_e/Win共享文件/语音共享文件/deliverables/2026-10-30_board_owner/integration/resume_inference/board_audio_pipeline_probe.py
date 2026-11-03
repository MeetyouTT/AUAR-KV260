"""Public-file-only ARM capture pipeline probe, using the real candidate pump.

No microphone, ALSA process, playback, GUI switch, DB or system tuning occurs.
The original BoardAutomaticCapture consumer and frontend factory are exercised
with a paced public-wave source in place of arecord stdout. A bounded queue
passing does NOT establish hard 20 ms model processing or physical capture.
"""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import signal
import statistics
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import urllib.request
import wave


MODEL_SHA = 'f36a0433bcf096bd6d6f11b80a3ac8bed110bdca632fe0d731df8d1a84475945'
TOKENS_SHA = '59aba8873a2ed1e122c25fee421e25f283b63290efbde85c1f01a853d83cb6e6'
WAV_SHA = '1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c'


class PublicPipelineFailure(RuntimeError):
    def __init__(self, code, diagnostics):
        self.code, self.diagnostics = code, diagnostics
        super().__init__(code)


class ProbePriorityError(RuntimeError):
    def __init__(self,code):
        self.code = code
        super().__init__(code)


def self_thread_ids():
    """Fresh Linux self-task membership; never enumerates another process."""
    pid = os.getpid()
    result = []
    for path in Path('/proc/self/task').iterdir():
        if not path.name.isdigit():
            continue
        try:
            fields = dict(line.split(':',1) for line in (path/'status').read_text().splitlines() if ':' in line)
        except (FileNotFoundError, ProcessLookupError):
            continue
        if int(fields['Tgid'].strip()) != pid:
            raise ProbePriorityError('probe_thread_membership_rejected')
        result.append(int(path.name))
    if pid not in result:
        raise ProbePriorityError('probe_main_thread_unavailable')
    return sorted(result)


def _nice_counts(values):
    result = {}
    for value in values.values():
        key = str(value)
        result[key] = result.get(key,0)+1
    return result


class ProbeProcessPriority:
    """Own probe task group only, before runtime threads are created.

    Existing self threads restore their individual starting nice. New runtime
    threads inherit the selected main-thread priority and are restored to its
    ORIGINAL priority. Vanished self threads are not signalled or recreated.
    Permission failure refuses the experiment before importing models.
    """
    def __init__(self,requested,*,api=os,thread_ids=None):
        if type(requested) is not int or requested not in (0,-5,-10):
            raise ValueError('Explicit diagnostic nice is 0, -5 or -10')
        self.requested,self.api = requested,api
        self.thread_ids = thread_ids or self_thread_ids
        self.pid = api.getpid()
        self.original = {}
        self.changed = False
        self.record = dict(requested_nice=requested,scope='current probe TGID and its own tasks only',
            original_nice=None,effective_nice=None,restored_nice=None,
            restoration_confirmed=False,permission_denied=False)

    def _read(self):
        values = {}
        for tid in self.thread_ids():
            try:
                values[tid] = self.api.getpriority(self.api.PRIO_PROCESS,tid)
            except ProcessLookupError:
                continue
        return values

    def _set_owned(self,tid,value):
        if tid not in self.thread_ids():  # Recheck self membership immediately before mutation.
            return
        try:
            current = self.api.getpriority(self.api.PRIO_PROCESS,tid)
            if current != value:
                self.api.setpriority(self.api.PRIO_PROCESS,tid,value)
                self.changed = True
        except ProcessLookupError:
            pass

    def __enter__(self):
        if not all(hasattr(self.api,key) for key in ('PRIO_PROCESS','getpriority','setpriority')):
            raise ProbePriorityError('process_nice_not_supported')
        self.original = self._read()
        if self.pid not in self.original:
            raise ProbePriorityError('probe_main_thread_unavailable')
        self.record['original_nice'] = self.original[self.pid]
        self.record['original_thread_nice_counts'] = _nice_counts(self.original)
        try:
            for tid in self.original:
                self._set_owned(tid,self.requested)
            effective = self._read()
            self.record['effective_nice'] = effective.get(self.pid)
            self.record['effective_thread_nice_counts'] = _nice_counts(effective)
            if not effective or any(value != self.requested for value in effective.values()):
                raise ProbePriorityError('process_nice_effective_mismatch')
        except BaseException as exc:
            self.record['permission_denied'] = isinstance(exc,PermissionError)
            self._restore()
            if isinstance(exc,PermissionError):
                raise ProbePriorityError('process_nice_permission_denied') from None
            raise
        return self

    def _restore(self):
        if not self.original:
            return
        errors = 0
        finish = self._read()
        self.record['finish_thread_nice_counts'] = _nice_counts(finish)
        for _ in range(3):  # Bounded even if a faulty runtime keeps spawning tasks.
            for tid in self.thread_ids():
                target = self.original.get(tid,self.original[self.pid])
                try:
                    self._set_owned(tid,target)
                except (PermissionError,OSError):
                    errors += 1
            after = self._read()
            if all(value == self.original.get(tid,self.original[self.pid]) for tid,value in after.items()):
                break
        self.record['restored_nice'] = after.get(self.pid)
        self.record['restored_thread_nice_counts'] = _nice_counts(after)
        self.record['restore_errors'] = errors
        self.record['restoration_confirmed'] = (self.pid in after and errors == 0 and
            all(value == self.original.get(tid,self.original[self.pid]) for tid,value in after.items()))

    def __exit__(self,*_):
        self._restore()
        if not self.record['restoration_confirmed']:
            raise ProbePriorityError('process_nice_restore_failed')


def self_scheduler_snapshot():
    import resource
    usage = resource.getrusage(resource.RUSAGE_SELF)
    result = dict(tasks={},voluntary_context_switches=usage.ru_nvcsw,
        involuntary_context_switches=usage.ru_nivcsw)
    for tid in self_thread_ids():
        try:
            values = [int(x) for x in (Path('/proc/self/task')/str(tid)/'schedstat').read_text().split()]
            if len(values)>=3:
                result['tasks'][tid] = values[:3]
        except (OSError,ValueError):
            pass
    return result


def scheduler_delta(before,after):
    common = set(before['tasks']) & set(after['tasks'])
    sums = [sum(max(0,after['tasks'][tid][i]-before['tasks'][tid][i]) for tid in common) for i in range(3)]
    return dict(common_tasks=len(common),new_tasks=len(set(after['tasks'])-set(before['tasks'])),
        runtime_ms=round(sums[0]/1e6,3),runqueue_wait_ms=round(sums[1]/1e6,3),timeslices=sums[2],
        voluntary_context_switches=after['voluntary_context_switches']-before['voluntary_context_switches'],
        involuntary_context_switches=after['involuntary_context_switches']-before['involuntary_context_switches'],
        measurement='Existing self tasks only; schedstat runqueue wait may be disabled by kernel. Sleeping/synchronization is not runqueue wait.')


def _local_json(port,path):
    connection = http.client.HTTPConnection('127.0.0.1',port,timeout=1.)
    timer = response = None
    try:
        connection.connect()
        connected = connection.sock
        def expire():
            try:
                connected.shutdown(2)
            except OSError:
                pass
        timer = threading.Timer(1.,expire)
        timer.daemon = True
        timer.start()
        connection.request('GET',path,headers={'Connection':'close'})
        response = connection.getresponse()  # No redirects, proxy or name lookup.
        raw = response.read(1024*1024+1)
        if response.status != 200 or len(raw)>1024*1024:
            raise ValueError('Local telemetry framing rejected')
        return json.loads(raw)
    finally:
        if timer is not None:
            timer.cancel()
        if response is not None:
            response.close()
        connection.close()


def production_context():
    """Whitelisted rolling display and face workload counts; no identity IDs."""
    try:
        state = _local_json(8783,'/api/state')
        camera = _local_json(8790,'/health')
        display = state.get('avatar_display') or {}
        identity = camera.get('identity') or {}
        faces = identity.get('face_targets') or {}
        numeric = lambda value:type(value) in (int,float) and value == value and abs(value)<1e15
        def select(values,names):
            return {name:values.get(name) for name in names if numeric(values.get(name))}
        return dict(available=True,
            display=dict(select(display,('pushed','received','sequence','fps','p50_ms','p95_ms','p99_ms','max_ms','age_ms')),
                kind='native_sink_handoff' if display.get('kind') == 'native_sink_handoff' else 'other_or_unknown'),
            camera=select(camera,('people_count','capture_frames','detected_frames','capture_age_ms','observation_age_ms')),
            identity=dict(select(identity,('processed','discarded','pending_frames','last_inference_ms')),
                backend='DPU_SFACE_INT8' if identity.get('backend') == 'DPU_SFACE_INT8' else 'other_or_unknown',
                faces=select(faces,('processed','discarded','source_age_ms','last_inference_ms'))))
    except Exception as exc:
        return dict(available=False,error_type=type(exc).__name__)


def context_delta(before,after):
    def delta(values1,values2,key):
        a,b = values1.get(key),values2.get(key)
        return round(b-a,4) if type(a) in (int,float) and type(b) in (int,float) else None
    b_display,a_display = before.get('display',{}),after.get('display',{})
    b_identity,a_identity = before.get('identity',{}),after.get('identity',{})
    return dict(display_fps_change=delta(b_display,a_display,'fps'),
        display_p95_ms_change=delta(b_display,a_display,'p95_ms'),
        identity_processed_change=delta(b_identity,a_identity,'processed'),
        face_detector_processed_change=delta(b_identity.get('faces',{}),a_identity.get('faces',{}),'processed'),
        measurement='Two existing rolling UI snapshots, not per-trial fps or P95 distributions')


def statistics_ms(values):
    values = sorted(values)
    return dict(count=len(values), mean=round(statistics.mean(values), 4) if values else 0.,
        p95=round(values[int(.95*(len(values)-1))], 4) if values else 0.,
        maximum=round(max(values), 4) if values else 0.,
        over_20ms=sum(value>20 for value in values))


def timing_windows(values):
    """Expose startup/tail samples; a short failure is not steady evidence."""
    return dict(first_16_frames=statistics_ms(values[:16]),
        remaining_frames=statistics_ms(values[16:]),
        enough_remaining_for_steady_comparison=len(values)>=116,
        windows_50_frames=[dict(first_frame=start+1,last_frame=min(start+50,len(values)),
            **statistics_ms(values[start:start+50])) for start in range(0,len(values),50)])


class PacedPublicPcm:
    """A finite public input clock; contains no model or endpoint calls."""
    def __init__(self, pcm, *, frame_seconds=.02):
        if not isinstance(pcm, bytes) or not pcm or len(pcm)%640:
            raise ValueError('Use complete public PCM16 frames')
        if type(frame_seconds) not in (int,float) or not .001<=frame_seconds<=.1:
            raise ValueError('Bound public input cadence')
        self.pcm, self.frame_seconds = pcm, frame_seconds
        self.stop_event = threading.Event()
        self.origin = None
        self.frames = 0
        self.lateness_ms = []
        self.reader_thread = None

    def read(self, size):
        if size != 640:
            raise ValueError('Public source requires one 20 ms frame')
        self.reader_thread = threading.current_thread().name
        if self.origin is None:
            self.origin = time.monotonic()
        if self.frames*640 >= len(self.pcm) or self.stop_event.is_set():
            return b''
        target = self.origin+(self.frames+1)*self.frame_seconds
        if self.stop_event.wait(max(0., target-time.monotonic())):
            return b''
        self.lateness_ms.append(max(0., (time.monotonic()-target)*1000))
        offset = self.frames*640
        self.frames += 1
        return self.pcm[offset:offset+640]

    def stop(self):
        self.stop_event.set()


def safety_snapshot(*,include_service_pids=True):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:8783/api/state', timeout=2) as response:
        raw = response.read(1024*1024+1)
    if len(raw)>1024*1024:
        raise ValueError('State exceeds bound')
    value = json.loads(raw)
    hands, pan = value.get('handsfree_dialogue', {}), value.get('manual_pan', {})
    if (value.get('phase') != 'IDLE' or value.get('playing') is not False
            or hands.get('enabled') is not False or hands.get('microphone_open') is not False
            or pan.get('automatic_following') is not False):
        raise ValueError('Explicit idle/device protection precondition failed')
    result = dict(phase='IDLE', playing=False, listening=False, microphone_open=False,
                  following=False, pan_state=pan.get('state'), pulse_us=pan.get('pulse_us'))
    result['boot_id'] = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    if include_service_pids:
        for role, unit in (('ui_pid','aura-avatar-ui.service'), ('camera_pid','aura-camera-ui.service')):
            result[role] = int(subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],
                                                      text=True, timeout=2).strip())
            if result[role] <= 0:
                raise ValueError('Required production service is not running')
    return result


def run_probe(args):
    if platform.machine().lower() not in ('aarch64','arm64'):
        raise ValueError('Actual ARM-only model probe; use synthetic unit tests on Windows')
    import resource
    root = args.resources_root.resolve()
    code = args.code_root.resolve()
    asr = root/'asr-1.13.8'
    fft = root/'fft-ee19b936d17aa451'
    frontend = root/'frontend-b3d06b653876469d'/'models'
    if not code.is_dir() or not (asr/'deps').is_dir() or not (fft/'deps').is_dir():
        raise ValueError('Use already staged isolated candidate dependencies')
    sys.path[:0] = [str(code), str(fft/'deps'), str(asr/'deps')]
    import numpy as np
    import onnxruntime as ort
    import sherpa_onnx as sherpa
    if (ort.__version__ != '1.17.3' or sherpa.__version__ != '1.13.8'
            or (fft/'deps').resolve() not in Path(ort.__file__).resolve().parents
            or (asr/'deps').resolve() not in Path(sherpa.__file__).resolve().parents):
        raise ValueError('Require the previously verified isolated ORT/sherpa versions')
    from board.runtime.audio.board_capture import BoardAutomaticCapture, BoardFrontendPool
    from board.runtime.audio.board_pcm_queue import BoundedPcmCaptureMixin
    from board.runtime.audio.board_gtcrn_fft import BoardFftSpeechGate
    from board.runtime.audio.board_asr import BoardParaformer
    if not issubclass(BoardAutomaticCapture, BoundedPcmCaptureMixin):
        raise ValueError('Probe requires the actual bounded capture factory integration')

    before = safety_snapshot(include_service_pids=False)
    available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                         if line.startswith('MemAvailable:')))
    if available < 1500000:
        raise ValueError('Insufficient headroom for isolated same-model probe')
    source = asr/'models/paraformer/test_wavs/0.wav'
    if source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest() != WAV_SHA:
        raise ValueError('Pinned upstream public WAV differs')
    with wave.open(str(source), 'rb') as wav:
        if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate()) != (1,2,16000):
            raise ValueError('Pinned public source must remain 16 kHz mono PCM16')
        pcm = wav.readframes(wav.getnframes())
    # Keep the final partial public frame exact, pad only its missing samples,
    # then supply explicit silence for the unchanged 700 ms endpoint rule.
    framed = pcm + bytes((-len(pcm))%640) + bytes(640*70)
    input_stream = PacedPublicPcm(framed)
    processing, decisions = [], []
    at = time.monotonic()
    gate = BoardFftSpeechGate(frontend, num_threads=args.num_threads, profile=True)
    gate_load_seconds = time.monotonic()-at
    pool = BoardFrontendPool(gate)

    if args.mode == 'frontend-profile':
        # Explicit component diagnosis: no paced input/pump/ASR acceptance is
        # claimed. More queue capacity cannot hide a throughput deficit here.
        runs = []
        try:
            for index in range(args.runs):
                lease = pool.acquire()
                durations,decisions = [],[]
                stages = {name:[] for name in ('fft_ms','ort_ms','ifft_ola_ms')}
                production_before = production_context()
                scheduler_before = self_scheduler_snapshot()
                thread_nice = _nice_counts(ProbeProcessPriority(0)._read())
                began,cpu = time.monotonic(),time.process_time()
                try:
                    for offset in range(0,len(framed),640):
                        raw = framed[offset:offset+640]
                        values = np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768
                        at = time.monotonic()
                        decisions.append(bool(lease(values)))
                        durations.append((time.monotonic()-at)*1000)
                        for name in stages:
                            stages[name].append(gate.denoiser.last_timing[name])
                    elapsed = time.monotonic()-began
                    cpu_elapsed = time.process_time()-cpu
                    scheduler_after = self_scheduler_snapshot()
                    production_after = production_context()
                    runs.append(dict(run=index+1,model_reused=index>0,
                        measurement_stage='reused_model_state_reset' if index else 'first_after_32_zero_frame_constructor_warmup',
                        recurrent_state_reset=True,frames=len(durations),
                        input_seconds=len(framed)/32000,wall_seconds=round(elapsed,4),
                        processing_rtf=round(elapsed/(len(framed)/32000),4),
                        cpu_seconds=round(cpu_elapsed,4),
                        wall_minus_process_cpu_seconds=round(elapsed-cpu_elapsed,4),
                        cpu_percent_one_core=round(cpu_elapsed/elapsed*100,2),
                        scheduler=scheduler_delta(scheduler_before,scheduler_after),
                        effective_thread_nice_counts=thread_nice,
                        production_context=dict(before=production_before,after=production_after,
                            change=context_delta(production_before,production_after)),
                        frontend_processing_ms=statistics_ms(durations),
                        processing_windows=timing_windows(durations),
                        denoiser_stages_ms={name:statistics_ms(values) for name,values in stages.items()},
                        decision_sha256=hashlib.sha256(bytes(decisions)).hexdigest(),
                        hard_20ms_model_gate_passed=all(value<=20 for value in durations)))
                finally:
                    lease.close()
        finally:
            pool.close()
        after = safety_snapshot(include_service_pids=False)
        if before != after:
            raise ValueError('Production entry/device state changed during diagnostic')
        return dict(status='DIAGNOSTIC_FRONTEND_PROFILE_ONLY',actual_arm=True,
            source='existing_upstream_public_test_wavs/0.wav',source_wav_sha256=WAV_SHA,
            num_threads=args.num_threads,constructor_zero_warmup_frames=32,
            gate_load_seconds=round(gate_load_seconds,4),runs=runs,
            runtime=dict(onnxruntime=ort.__version__,sherpa_onnx=sherpa.__version__),
            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            asr_executed=False,paced_capture_acceptance=False,
            production_state_unchanged=True,hardware_actions=0,
            microphone_opened=False,production_database_opened=False,systemwide_tuning=False,
            acceptance_scope='Component diagnosis only: first measured/reused-model state-reset runs and 50-frame windows. Not capture or realtime acceptance.',
            before=before,after=after)

    class ObservedLease:
        def __init__(self, lease):
            self.lease = lease
        def __call__(self, frame):
            if threading.current_thread().name == 'aura-board-raw-pcm':
                raise AssertionError('Model work leaked into raw producer')
            began = time.monotonic()
            result = self.lease(frame)
            processing.append((time.monotonic()-began)*1000)
            decisions.append(bool(result))
            return result
        def close(self):
            self.lease.close()
        def public(self):
            return self.lease.public()

    def no_device(*args, **kwargs):
        raise AssertionError('Probe must not open a microphone process')

    capture = BoardAutomaticCapture(lambda: False, max_seconds=20,
        frontend_factory=lambda: ObservedLease(pool.acquire()), process_factory=no_device)
    capture.frontend_queue_frames = args.queue_frames
    capture.endpoint = capture._endpoint()
    # Only the public source is stopped here; no signal is sent to any PID.
    capture._signal = lambda signum: input_stream.stop()
    captured = None
    at, cpu_at = time.monotonic(), time.process_time()
    try:
        captured = capture._read_pcm(SimpleNamespace(stdout=input_stream))
        pipeline_seconds = time.monotonic()-at
        pipeline_cpu_seconds = time.process_time()-cpu_at
        queue = capture._board_pcm_input.public()
        offset = capture.endpoint.start_sample*2
        if (not captured or len(captured)%2 or len(captured)>20*32000
                or captured != framed[offset:offset+len(captured)]
                or queue['error'] or queue['reader_alive']):
            raise ValueError('Actual endpoint/pump did not preserve original contiguous PCM')
    except Exception as exc:
        pump = getattr(capture, '_board_pcm_input', None)
        raise PublicPipelineFailure(getattr(exc,'code','public_capture_failed'),
            dict(input_queue=pump.public() if pump is not None else None,
                frontend_processing_ms=statistics_ms(processing),
                processing_windows=timing_windows(processing),num_threads=args.num_threads,
                source_supply_lateness_ms=statistics_ms(input_stream.lateness_ms),
                produced_frames=input_stream.frames,asr_executed=False)) from None
    finally:
        input_stream.stop()
        pump = getattr(capture, '_board_pcm_input', None)
        if pump is not None:
            pump.close()
        capture._close_endpoint()
        if capture._timer is not None:
            capture._timer.cancel()
        pool.close()

    at = time.monotonic()
    decoder = BoardParaformer(asr/'models/paraformer', model_sha256=MODEL_SHA,
                              tokens_sha256=TOKENS_SHA, num_threads=2)
    asr_load_seconds = time.monotonic()-at
    at = time.monotonic()
    text = decoder.transcribe(captured, deadline=at+20.)
    asr_seconds = time.monotonic()-at
    after = safety_snapshot(include_service_pids=False)
    if before != after:
        raise ValueError('Production entry/device state changed during probe')
    return dict(status='PASS_PUBLIC_PCM_PUMP_ENDPOINT_AND_ASR', actual_arm=True,
        source='existing_upstream_public_test_wavs/0.wav', source_wav_sha256=WAV_SHA,
        resources=dict(paraformer_sha256=MODEL_SHA,tokens_sha256=TOKENS_SHA,
            onnxruntime=ort.__version__,sherpa_onnx=sherpa.__version__,numpy=np.__version__),
        num_threads=args.num_threads,constructor_zero_warmup_frames=32,
        gate_load_seconds=round(gate_load_seconds,4),
        pipeline_seconds=round(pipeline_seconds,4),
        pipeline_cpu_percent_one_core=round(pipeline_cpu_seconds/pipeline_seconds*100,2),
        producer_thread=input_stream.reader_thread,
        source_supply_lateness_ms=statistics_ms(input_stream.lateness_ms),
        frontend_processing_ms=statistics_ms(processing), input_queue=queue,
        processing_windows=timing_windows(processing),
        endpoint=dict(start_sample=capture.endpoint.start_sample,
            captured_samples=len(captured)//2,source_audio_seconds=round(len(pcm)/32000,4),
            captured_pcm_sha256=hashlib.sha256(captured).hexdigest(),
            original_contiguous_pcm_preserved=True,decision_sha256=hashlib.sha256(bytes(decisions)).hexdigest()),
        asr=dict(load_seconds=round(asr_load_seconds,4),decode_seconds=round(asr_seconds,4),
            result_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),result_characters=len(text)),
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        production_state_unchanged=True,hardware_actions=0,microphone_opened=False,
        production_database_opened=False,model_changed=False,systemwide_tuning=False,
        hard_20ms_model_gate_passed=all(value<=20 for value in processing),
        acceptance_scope='Finite paced public-file capture using actual bounded pump and original endpoint; not physical microphone/playback or hard realtime acceptance',
        before=before,after=after)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code-root', type=Path, required=True)
    parser.add_argument('--resources-root', type=Path, required=True)
    parser.add_argument('--queue-frames', type=int, default=8)
    parser.add_argument('--num-threads',type=int,choices=(1,2),default=1)
    parser.add_argument('--mode',choices=('pipeline','frontend-profile'),default='pipeline')
    parser.add_argument('--runs',type=int,choices=(1,2,3),default=1,
        help='Reused-model/state-reset repetitions for explicit frontend-profile mode only')
    parser.add_argument('--process-nice',type=int,choices=(0,-5,-10),default=0,
        help='Isolated probe-only priority experiment; permissions required and original priorities restored')
    args = parser.parse_args(argv)
    if not 1 <= args.queue_frames <= 64:
        parser.error('Bound queue to 1-64 frames')
    if args.mode == 'pipeline' and args.runs != 1:
        parser.error('Pipeline is one original capture; repeated diagnostics require frontend-profile mode')
    def expired(*_):
        raise TimeoutError('Public probe total deadline')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(90)
    priority = ProbeProcessPriority(args.process_nice)
    production_before = production_after = None
    safety_before = safety_after = None
    cleanup_error = None
    result_code = 0
    try:
        # The only short-lived systemctl helpers run at the ORIGINAL priority,
        # before the experiment and after restoration, never at negative nice.
        safety_before = safety_snapshot()
        with priority:
            production_before = production_context()
            try:
                value = run_probe(args)
            finally:
                production_after = production_context()
    except Exception as exc:
        value = dict(status='FAILED',error_type=type(exc).__name__,
            error_code=getattr(exc,'code','public_pipeline_probe_failed'),
            diagnostics=getattr(exc,'diagnostics',None),
            microphone_opened=False,production_changed=False)
        result_code = 2
    finally:
        signal.alarm(0)
        if safety_before is not None and priority.record['restoration_confirmed']:
            try:
                safety_after = safety_snapshot()
                if safety_before != safety_after:
                    cleanup_error = 'post_restore_safety_mismatch'
            except Exception:
                cleanup_error = 'post_restore_safety_unavailable'
    if cleanup_error:
        value['status'] = 'FAILED'
        value['error_code'] = cleanup_error
        result_code = 2
    value['process_priority'] = dict(priority.record,priority_changed=priority.changed)
    value['system_tuning'] = priority.changed
    value['systemwide_tuning'] = False
    value['own_process_priority_experiment'] = True
    value['outer_service_safety'] = dict(before=safety_before,after=safety_after,
        unchanged=safety_before is not None and safety_before == safety_after,
        systemctl_helpers_outside_priority_scope=True)
    if production_before is not None:
        value['production_context'] = dict(before=production_before,after=production_after,
            change=context_delta(production_before,production_after or {}))
    print(json.dumps(value,ensure_ascii=True),flush=True)
    return result_code


if __name__ == '__main__':
    raise SystemExit(main())
