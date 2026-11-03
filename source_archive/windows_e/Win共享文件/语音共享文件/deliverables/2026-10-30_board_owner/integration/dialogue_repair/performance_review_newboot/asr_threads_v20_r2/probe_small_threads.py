"""Root-owned Small 3/2/2/3 public-file pilot, dry by default."""
import argparse
import hashlib
import http.client
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
import wave

HERE=Path(__file__).resolve().parent
STARTUP='d24b0d0007e2aa2b417f459891c7f39f168502a58374334ceab69e31af5881dd'
BOOT='bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
ROOT='/home/root/aura-board-business-20261030/production-5259eab11e42af13'
CONFIG_SHA='5518b6705083eb9e2fae7e19a47c003182995fe8660cbc6031860c9905da9786'
ADAPTER_SHA='4edb865881c887d6a290a02e078e14386bd95d017b79820b143b5a1e329997c3'
MODEL_DIR='/home/root/aura-board-asr-models/paraformer-small-63ddc3cd0f2810b6'
MODEL_SHA='3ef6c19369b912f7caf3cef8e545c5ccd1a33d9d7ec792a46668dc41c4b229ec'
TOKEN_SHA='4b2d964e18b9cf139b473003b6698fb2ed9a2a5ec55b93daa677b28f578897aa'
HELPER_SHA='293b23f5dd350e5f4d1cce1489120a44b2c4d743c1534080da496f3f58407176'
FIXTURE_MANIFEST='/home/root/aura-public-streaming-validation-20261031/synthetic-8a9983b6bb9f42c6/manifest.json'
FIXTURE_SHA='7109ee213126f098a3a3da08bbc521beb0db54a21e0911be02e04f2010b9a869'
WAV0='/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/models/paraformer/test_wavs/0.wav'
WAV0_SHA='1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c'
ASR_DEPS='/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps'
ORDER=(3,2,2,3)
CHILD_ERROR_CODES = frozenset({
    'ACTUAL_BOARD_REQUIRED',
    'ASR_RESULT_INVALID',
    'BASELINE_CHANGED',
    'BOOT_CHANGED',
    'CAMERA_HEALTH_OWNER_CHANGED',
    'COMPONENT_MAP_CHANGED',
    'EXTERNAL_DEADLINE_REQUIRED',
    'FIXTURE_ORDER_CHANGED',
    'FileNotFoundError',
    'GUI_MUST_REMAIN_VISIBLE',
    'INSUFFICIENT_ASR_HEADROOM',
    'INTERNAL_SLOT_ARGUMENT_REQUIRED',
    'ImportError',
    'MODEL_PATH_REJECTED',
    'MemoryError',
    'ModuleNotFoundError',
    'OSError',
    'OWNED_ASR_SLOT_FAILED',
    'OWNED_PROCESS_PROOF_LOST',
    'OWNED_SLOT_RESULT_REJECTED',
    'PACKAGE_FILE_REJECTED',
    'PATH_REJECTED',
    'PROBE_CONFIGURATION_REJECTED',
    'PROBE_DEADLINE',
    'PRODUCTION_ASR_CONFIGURATION_CHANGED',
    'PRODUCTION_OWNER_CHANGED',
    'PUBLIC_PCM_INCOMPLETE',
    'PUBLIC_WAV0_FORMAT_CHANGED',
    'PermissionError',
    'RECOGNIZER_CONFIGURATION_CHANGED',
    'ROOT_MUST_PAUSE_REAL_CAPTURE_FIRST',
    'Refused',
    'RuntimeError',
    'SHERPA_VERSION_CHANGED',
    'SIZE_REJECTED',
    'SOURCE_PIN_CHANGED',
    'STATE_UNAVAILABLE',
    'TimeoutError',
    'TypeError',
    'UNREVIEWED_PRIORITY_OR_AFFINITY',
    'ValueError',
})


class Refused(RuntimeError):
    pass


def require(value,code):
    if not value:raise Refused(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_pinned(path,fingerprint,maximum=262144):
    path=Path(path)
    require(path.is_file() and path.resolve()==path and not path.is_symlink(),'PATH_REJECTED')
    require(0<=path.stat().st_size<=maximum,'SIZE_REJECTED')
    raw=path.read_bytes()
    require(sha(raw)==fingerprint,'SOURCE_PIN_CHANGED')
    return raw


def get_metadata(port,route):
    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
    try:
        connection.request('GET',route)
        response=connection.getresponse();raw=response.read(1048577)
        require(response.status==200 and len(raw)<=1048576,'STATE_UNAVAILABLE')
        return json.loads(raw)
    finally:connection.close()


def number(value):
    return value if type(value) in (int,float) and math.isfinite(value) and value>=0 else None


def process_identity(pid):
    path=Path('/proc')/str(pid)
    fields=(path/'stat').read_text().rsplit(')',1)[1].split()
    return dict(pid=pid,birth_ticks=int(fields[19]),command_sha256=sha((path/'cmdline').read_bytes()))


def available_mib():
    rows=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
    return int(rows['MemAvailable'].split()[0])/1024


def guard(baseline,full=False):
    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'BOOT_CHANGED')
    root=Path(ROOT)
    startup=json.loads(read_pinned(root/'startup/config.json',STARTUP))
    require(len(baseline['component_pins'])==380 and startup['component_sha256']==baseline['component_pins'],'COMPONENT_MAP_CHANGED')
    if full:
        for relative,fingerprint in baseline['component_pins'].items():
            read_pinned(root/'runtime/aura'/relative,fingerprint,16*1024*1024)
    config=json.loads(read_pinned(root/'runtime/aura/config/board_avatar_gtk.json',CONFIG_SHA))
    options=config['board_business']
    require(options['asr_variant']=='paraformer_small' and options['asr_threads']==3
        and options['asr_directory']==MODEL_DIR,'PRODUCTION_ASR_CONFIGURATION_CHANGED')
    for role in ('supervisor','gtk','camera'):
        require(process_identity(baseline[role]['pid'])==baseline[role],'PRODUCTION_OWNER_CHANGED')
    state=get_metadata(8783,'/api/state');listening=state.get('handsfree_dialogue',{})
    require(state.get('phase')=='IDLE' and state.get('playing') is False
        and listening.get('enabled') is False and listening.get('microphone_open') is False
        and listening.get('state')=='PAUSED'
        and state.get('local_transcription',{}).get('state') not in ('TRANSCRIBING','GENERATING','PLAYING'),
        'ROOT_MUST_PAUSE_REAL_CAPTURE_FIRST')
    native=state.get('avatar_display',{})
    require(native.get('visible') is True and native.get('frame_scheduling_active') is True,'GUI_MUST_REMAIN_VISIBLE')
    require(available_mib()>=1500,'INSUFFICIENT_ASR_HEADROOM')
    memory=state.get('board_business',{}).get('memory',{})
    camera=get_metadata(8790,'/health')
    require(camera.get('pid')==baseline['camera']['pid'],'CAMERA_HEALTH_OWNER_CHANGED')
    return dict(observed_mono=time.monotonic(),native_frames=number(native.get('frames')),
        native_paint_at=number(native.get('paint_at')),native_age_ms=number(native.get('age_ms')),
        memory_completed=number(memory.get('completed')),memory_discarded=number(memory.get('discarded')),
        camera={key:number(camera.get(key)) for key in ('capture_frames','detected_frames','preview_frames',
            'capture_age_ms','observation_age_ms','last_inference_ms')},
        available_mib=available_mib(),listening_paused=True,owners_verified=True)


def load_helper():
    raw=read_pinned(HERE/'public_quality_helper.py',HELPER_SHA,65536)
    spec=importlib.util.spec_from_loader('_public_audio_helper',loader=None)
    helper=importlib.util.module_from_spec(spec)
    exec(compile(raw,'<pinned-public-audio-helper>','exec'),helper.__dict__)
    return helper


def public_audio(helper):
    manifest=json.loads(read_pinned(FIXTURE_MANIFEST,FIXTURE_SHA,65536))
    existing=helper.validate_manifest(manifest)
    s01=next((case,pcm) for case,spans,pcm in existing if case['id']=='S01')
    raw=read_pinned(WAV0,WAV0_SHA,1024*1024)
    with wave.open(io.BytesIO(raw),'rb') as stream:
        require((stream.getnchannels(),stream.getsampwidth(),stream.getframerate(),stream.getnframes(),stream.getcomptype())
                ==(1,2,16000,89834,'NONE'),'PUBLIC_WAV0_FORMAT_CHANGED')
        pcm=stream.readframes(89834)
    require(len(pcm)==89834*2,'PUBLIC_PCM_INCOMPLETE')
    rows=[(dict(id='P00',sha256=WAV0_SHA,samples=89834),pcm),s01]
    require([row['id'] for row,pcm in rows]==['P00','S01'],'FIXTURE_ORDER_CHANGED')
    return rows


def decode(model,case,pcm,helper,deadline):
    began=time.perf_counter();cpu=time.process_time()
    text=model.transcribe(pcm,sample_rate=16000,deadline=min(deadline,time.monotonic()+25))
    elapsed=(time.perf_counter()-began)*1000;used=(time.process_time()-cpu)*1000
    require(isinstance(text,str) and 0<len(text)<=1000,'ASR_RESULT_INVALID')
    normalized=helper.normalized(text)
    require(bool(normalized),'ASR_RESULT_INVALID')
    return dict(id=case['id'],wav_sha256=case['sha256'],pcm_sha256=sha(pcm),
        samples=len(pcm)//2,rate=16000,audio_seconds=len(pcm)/32000,
        decode_wall_ms=elapsed,decode_process_cpu_ms=used,real_time_factor=elapsed/(len(pcm)/32),
        result_sha256=sha(text.encode('utf8')),normalized_sha256=sha(normalized.encode('utf8')))


def slot(threads,baseline,deadline):
    slot_started=time.perf_counter()
    require(threads in (2,3) and os.getpriority(os.PRIO_PROCESS,0)==0,'PROBE_CONFIGURATION_REJECTED')
    before=guard(baseline)
    helper=load_helper();audio=public_audio(helper)
    adapter=Path(ROOT)/'runtime/aura/board/runtime/audio/board_asr.py'
    read_pinned(adapter,ADAPTER_SHA,32768)
    require(Path(MODEL_DIR).resolve()==Path(MODEL_DIR),'MODEL_PATH_REJECTED')
    sys.path[:0]=[str(Path(ROOT)/'runtime/aura'),ASR_DEPS]
    wall=time.perf_counter();cpu=time.process_time()
    with helper.quiet_native():
        from board.runtime.audio.board_asr import BoardParaformer
        from sherpa_onnx import OfflineRecognizer,__version__
        require(__version__=='1.13.8','SHERPA_VERSION_CHANGED')
        imports=dict(wall_ms=(time.perf_counter()-wall)*1000,process_cpu_ms=(time.process_time()-cpu)*1000)
        native_load={}
        def factory(**kwargs):
            require(not native_load and kwargs['num_threads']==threads,'RECOGNIZER_CONFIGURATION_CHANGED')
            started=time.perf_counter();cpu_started=time.process_time()
            recognizer=OfflineRecognizer.from_paraformer(**kwargs)
            native_load.update(wall_ms=(time.perf_counter()-started)*1000,
                process_cpu_ms=(time.process_time()-cpu_started)*1000)
            return recognizer
        wall=time.perf_counter();cpu=time.process_time()
        model=BoardParaformer(MODEL_DIR,model_sha256=MODEL_SHA,tokens_sha256=TOKEN_SHA,
            num_threads=threads,recognizer_factory=factory)
        construction=dict(wall_ms=(time.perf_counter()-wall)*1000,process_cpu_ms=(time.process_time()-cpu)*1000)
        require(time.monotonic()<deadline,'PROBE_DEADLINE')
        guard(baseline)
        warmups=[]
        for case,pcm in audio:
            guard(baseline)
            warmups.append(decode(model,case,pcm,helper,deadline))
        measured_before=guard(baseline)
        measurements=[]
        for case,pcm in audio:
            guard(baseline)
            measurements.append(decode(model,case,pcm,helper,deadline))
        measured_after=guard(baseline)
    import resource
    after=guard(baseline)
    return dict(status='PUBLIC_ASR_SLOT_MEASURED',threads=threads,
        imports=imports,constructor_total=construction,native_recognizer_construction=native_load,
        constructor_includes_adapter_resource_hashing=True,warmups=warmups,measurements=measurements,
        before=before,after=after,measurement_window_before=measured_before,measurement_window_after=measured_after,
        slot_wall_seconds=time.perf_counter()-slot_started,process_cpu_seconds=time.process_time(),
        process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        process_thread_count=sum(path.name.isdigit() for path in Path('/proc/self/task').iterdir()),
        background_counter_changed=any(before[key]!=after[key] for key in ('memory_completed','memory_discarded')),
        independent_asr_process=True,production_asr_remains_resident=True,
        model_sha256=MODEL_SHA,tokens_sha256=TOKEN_SHA,adapter_sha256=ADAPTER_SHA,
        startup_sha256=STARTUP,normalizer='NFKC_casefold_isalnum',
        raw_transcript_exported=False,microphone_opened=False,audio_played=False,
        llm_or_tts_request_sent=False,production_database_opened=False,production_configuration_written=False)


def allowed_child_code(value):
    return value if type(value) is str and len(value)<=64 and value in CHILD_ERROR_CODES else None


def child_error_code(stdout):
    if type(stdout) is not str or len(stdout)>=65536:
        return None
    try:
        value=json.loads(stdout)
    except (ValueError,RecursionError):
        return None
    if not isinstance(value,dict) or value.get('status')!='REFUSED':
        return None
    return allowed_child_code(value.get('error_code'))


def run_child(threads,package_sha,deadline):
    command=[sys.executable,'-B',str(Path(__file__).resolve()),'--execute-root-only',
        '--package-sha256',package_sha,'--slot',str(threads),'--deadline',str(deadline)]
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
        start_new_session=True,env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
        MKL_NUM_THREADS='1',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1'))
    identity=None
    try:
        identity=process_identity(process.pid)
        stdout,stderr=process.communicate(timeout=min(45,max(.1,deadline-time.monotonic())))
        require(len(stdout)<65536,'OWNED_ASR_SLOT_FAILED')
        if process.returncode!=0:
            error=Refused('OWNED_ASR_SLOT_FAILED')
            error.child_error_code=child_error_code(stdout)
            raise error
        value=json.loads(stdout)
        require(value.get('status')=='PUBLIC_ASR_SLOT_MEASURED' and value.get('threads')==threads,'OWNED_SLOT_RESULT_REJECTED')
        return value
    finally:
        if process.poll() is None:
            if identity is None:identity=process_identity(process.pid)
            require(process_identity(process.pid)==identity and os.getpgid(process.pid)==process.pid
                and process.pid!=os.getpgrp(),'OWNED_PROCESS_PROOF_LOST')
            os.killpg(process.pid,signal.SIGTERM)
            try:process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                require(process_identity(process.pid)==identity,'OWNED_PROCESS_PROOF_LOST')
                os.killpg(process.pid,signal.SIGKILL);process.communicate(timeout=5)
        try:os.killpg(process.pid,0)
        except ProcessLookupError:pass
        else:raise Refused('OWNED_ASR_GROUP_REMAINS')


def package(expected):
    manifest=json.loads(read_pinned(HERE/'PACKAGE_MANIFEST.json',expected))
    for relative,row in manifest['files'].items():
        require(relative in ('probe_small_threads.py','compare_results.py','baseline.json','public_quality_helper.py'),
                'PACKAGE_FILE_REJECTED')
        read_pinned(HERE/relative,row['sha256'],1024*1024)
    baseline=json.loads((HERE/'baseline.json').read_bytes())
    require(baseline['startup_sha256']==STARTUP and baseline['boot_id']==BOOT and baseline['root']==ROOT,'BASELINE_CHANGED')
    return baseline


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--package-sha256',required=True)
    parser.add_argument('--execute-root-only',action='store_true')
    parser.add_argument('--slot',type=int,choices=(2,3),help=argparse.SUPPRESS)
    parser.add_argument('--deadline',type=float,help=argparse.SUPPRESS)
    args=parser.parse_args();baseline=package(args.package_sha256)
    if not args.execute_root_only:
        return dict(status='DRY_PACKAGE_VALIDATED',order=list(ORDER),warmups_per_slot=2,measured_decodes_per_slot=2)
    require(platform.system()=='Linux' and platform.machine()=='aarch64','ACTUAL_BOARD_REQUIRED')
    require(os.getpriority(os.PRIO_PROCESS,0)==0 and len(os.sched_getaffinity(0))==4,'UNREVIEWED_PRIORITY_OR_AFFINITY')
    if args.slot is not None:
        require(args.deadline is not None and 0<args.deadline-time.monotonic()<=140,'EXTERNAL_DEADLINE_REQUIRED')
        return slot(args.slot,baseline,args.deadline)
    require(args.deadline is None,'INTERNAL_SLOT_ARGUMENT_REQUIRED')
    guard(baseline,full=True)
    deadline=time.monotonic()+140
    results=[]
    try:
        for threads in ORDER:
            require(deadline-time.monotonic()>5,'PROBE_DEADLINE')
            guard(baseline)
            results.append(run_child(threads,args.package_sha256,deadline))
        guard(baseline)
        return dict(status='PUBLIC_ABBA_COMPLETE',order=list(ORDER),results=results,
            baseline_sha256=sha((HERE/'baseline.json').read_bytes()),startup_sha256=STARTUP,
            comparison_is_pilot=True,production_changed=False)
    except Exception as error:
        return dict(status='PUBLIC_ABBA_STOPPED',order=list(ORDER),results=results,
            error_code=str(error) if isinstance(error,Refused) else type(error).__name__,
            child_error_code=allowed_child_code(getattr(error,'child_error_code',None)),production_changed=False)


if __name__=='__main__':
    try:
        value=main();print(json.dumps(value,allow_nan=False))
        raise SystemExit(0 if value['status'] in ('DRY_PACKAGE_VALIDATED','PUBLIC_ASR_SLOT_MEASURED','PUBLIC_ABBA_COMPLETE') else 2)
    except Exception as error:
        print(json.dumps(dict(status='REFUSED',error_code=str(error) if isinstance(error,Refused) else type(error).__name__)))
        raise SystemExit(2)
