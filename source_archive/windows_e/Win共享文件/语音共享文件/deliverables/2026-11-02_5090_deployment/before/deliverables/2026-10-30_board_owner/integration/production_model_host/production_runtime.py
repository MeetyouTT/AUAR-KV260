"""Persistent, explicitly controlled model-only owner. No business imports.

This process has no TTL. Its stop marker closes only its server and owned RAM
TTS. Releasing its own fixed27B is separate, explicit and proven while idle.
Project Ollama and all unrelated daemons/processes are never terminated.
"""
import argparse
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import socket
import sys
import threading
import time
import uuid

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
AURA=PROJECT/'aura'
sys.path[:0]=[str(AURA),str(PROJECT/'deliverables/2026-10-18_board_dialogue')]
CONFIG=AURA/'config/model_inference.local.json'
RUNTIME=PROJECT/'deliverables/2026-10-18_board_dialogue/model_host'
MODEL='aura-qwen3.8-27b-abliterated:iq4_xs'


def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(raw):return hashlib.sha256(raw).hexdigest()


def write_json(path,value):
    path=Path(path)
    raw=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    temporary=path.with_name(path.name+'.part-'+uuid.uuid4().hex)
    try:
        with temporary.open('xb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
        os.replace(str(temporary),str(path))
    finally:temporary.unlink(missing_ok=True)


def config():
    raw=CONFIG.read_bytes()
    if len(raw)>16384:raise ValueError('configuration_size')
    value=json.loads(raw)
    expected=dict(schema_version=1,host='192.168.50.1',port=8797,
        allowed_peers=['192.168.50.2'],local_health=True,startup_seconds=300,lifetime_seconds=None)
    if set(value)!=set(expected)|{'voice_python'} or any(value[k]!=v for k,v in expected.items()):
        raise ValueError('fixed_inference_configuration_required')
    if not isinstance(value['voice_python'],str) or not Path(value['voice_python']).is_file():
        raise ValueError('voice_python_unavailable')
    return value,digest(raw)


def control(path,session):
    if not path.exists():return None
    raw=path.read_bytes()
    if len(raw)>1024:raise ValueError('control_size')
    value=json.loads(raw)
    if (not isinstance(value,dict) or set(value)!={'session_id','control_id','action'}
            or value['session_id']!=session or re.fullmatch('[0-9a-f]{32}',value.get('control_id','')) is None
            or value['action'] not in ('stop','release_owned_model')):
        raise ValueError('invalid_control')
    return value


def ollama_json(method,path,body=None,*,timeout=5.):
    connection=http.client.HTTPConnection('127.0.0.1',11435,timeout=timeout)
    timer=None
    try:
        connection.connect();actual=connection.sock
        def expire():
            try:actual.shutdown(socket.SHUT_RDWR)
            except OSError:pass
        timer=threading.Timer(timeout,expire);timer.daemon=True;timer.start()
        encoded=json.dumps(body).encode() if body is not None else None
        connection.request(method,path,body=encoded,headers={'Content-Type':'application/json'})
        response=connection.getresponse();raw=response.read(65537)
        if response.status!=200 or len(raw)>65536:raise RuntimeError('owned_model_control_failed')
        return json.loads(raw)
    finally:
        if timer:timer.cancel()
        connection.close()


def require_owned_model(state):
    """Read-only proof, never accepts arbitrary PID/model/host arguments."""
    from project_ollama import inspect_ownership
    if state.get('owns_fixed_model') is not True:raise RuntimeError('fixed_model_not_owned')
    current=inspect_ownership();expected=state['fixed_daemon_owner']
    if any(current.get(k)!=expected.get(k) for k in ('pid','creation_utc','executable','command_line','listeners')):
        raise RuntimeError('fixed_daemon_owner_changed')
    rows=ollama_json('GET','/api/ps').get('models')
    if (not isinstance(rows,list) or len(rows)>1 or any(not isinstance(row,dict)
            or row.get('name')!=MODEL or row.get('model',MODEL)!=MODEL for row in rows)):
        raise RuntimeError('fixed_model_residency_changed')
    return bool(rows)


def release_owned_model(state):
    resident=require_owned_model(state)
    if resident:
        value=ollama_json('POST','/api/generate',dict(model=MODEL,prompt='',stream=False,keep_alive=0),timeout=10.)
        if value.get('model')!=MODEL or value.get('done') is not True or value.get('response')!='':
            raise RuntimeError('owned_model_release_failed')
    if require_owned_model(state):raise RuntimeError('owned_model_release_unconfirmed')
    return dict(released=True,was_resident=resident,model=MODEL,
        project_daemon_stopped=False,unrelated_models_stopped=False)


def safe_error(error):
    code=getattr(error,'code','')
    if not isinstance(code,str) or re.fullmatch('[a-z][a-z0-9_]{0,79}',code) is None:
        code='model_owner_operation_failed'
    return dict(error_type=type(error).__name__,error_code=code)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session-id',required=True)
    args=parser.parse_args(argv)
    if re.fullmatch('[0-9a-f]{32}',args.session_id) is None:parser.error('fresh session identifier required')
    output=HERE/'sessions'/args.session_id
    output.mkdir(parents=True,exist_ok=False)
    # Native/model diagnostics are intentionally discarded; state files contain
    # metadata only. Request bodies, response text and PCM never reach logs.
    sys.stdout=open(os.devnull,'w');sys.stderr=open(os.devnull,'w')
    os.environ['OLLAMA_DEBUG']='false'
    state=dict(schema_version=1,session_id=args.session_id,pid=os.getpid(),status='STARTING',
        role='model_inference_only',started_utc=utc(),lifetime_seconds=None,
        business_database_opened=False,request_logging=False,raw_audio_archived=False,
        owns_fixed_model=False,owner_protocol='aura.production-model-owner-1')
    state_path=output/'status.json';stop_path=output/'CONTROL.json'
    write_json(state_path,state)
    startup_cancel=threading.Event();watch_done=threading.Event()
    def watch_startup():
        while not watch_done.wait(.1):
            try:
                request=control(stop_path,args.session_id)
                if request and request['action']=='stop':startup_cancel.set();return
            except (OSError,ValueError,TypeError):pass
    watcher=threading.Thread(target=watch_startup,daemon=True,name='inference-startup-stop');watcher.start()
    backend=models=server=server_thread=lock=None
    requested=None;release=False;result_code=0
    try:
        value,configuration_sha=config()
        if Path(sys.executable).resolve()!=Path(value['voice_python']).resolve():
            raise ValueError('explicit_voice_python_required')
        from tools.service_instance_lock import ServiceInstanceLock
        from tools.voice_startup_guard import cold_capacity_preflight
        from tools.model_inference_startup import startup_models
        from tools.model_inference_host import LocalModelBackend,InferenceHost,make_server
        from project_ollama import ensure
        RUNTIME.mkdir(parents=True,exist_ok=True)
        lock=ServiceInstanceLock(RUNTIME/'voice8792.instance.lock')
        lock.acquire()
        deadline=time.monotonic()+300.
        if startup_cancel.is_set():raise InterruptedError()
        # The lifetime lock is acquired BEFORE creation/reuse of project
        # Ollama. Never adopts a mismatched live process environment.
        daemon=ensure()
        if not daemon.get('ready') or daemon.get('needs_controlled_restart'):
            raise RuntimeError('project_daemon_binding_not_ready')
        state.update(configuration_sha256=configuration_sha,
            fixed_daemon_pid=daemon['ownership']['pid'],fixed_daemon_owner=daemon['ownership'])
        initial=cold_capacity_preflight(AURA,RUNTIME,lock=lock,
            listen=value['host'],port=8792,deadline=deadline)
        if startup_cancel.is_set():raise InterruptedError()
        backend=LocalModelBackend.from_config(voice_python=value['voice_python'])
        startup=startup_models(backend,lock=lock,deadline=deadline,cancelled=startup_cancel)
        state['owns_fixed_model']=initial['extra']['project_model_resident'] is False
        models=InferenceHost(backend)
        server=make_server((value['host'],value['port']),models,
            allowed_peers=value['allowed_peers'],local_health=value['local_health'])
        server_thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.1},
            name='production-model-http',daemon=True);server_thread.start()
        watch_done.set();watcher.join(timeout=.5)
        state.update(status='READY',startup=startup,ready_utc=utc(),
            listen=value['host'],port=value['port'],same_unique_tts_pid=backend.voice.process.pid,
            control_path=str(stop_path),health_path='/health',model=MODEL)
        write_json(state_path,state)
        while True:
            if not server_thread.is_alive():raise RuntimeError('model_http_owner_stopped')
            request=control(stop_path,args.session_id)
            if request:
                if request['action']=='release_owned_model':
                    with models.condition:
                        if models.active is not None or models.pending or models.jobs:
                            state['last_control']=dict(control_id=request['control_id'],status='REJECTED',reason='foreground_not_idle')
                            write_json(state_path,state);stop_path.unlink();continue
                        # Temporarily close admission while proving model
                        # ownership; restore it on any proof failure.
                        models.closed=True
                        try:require_owned_model(state)
                        except Exception as error:
                            models.closed=False
                            state['last_control']=dict(control_id=request['control_id'],status='REJECTED',reason='ownership_not_proven',**safe_error(error))
                            write_json(state_path,state);stop_path.unlink();continue
                    release=True
                requested=request
                break
            time.sleep(.15)
        state.update(status='STOPPING',last_control=dict(control_id=requested['control_id'],status='ACCEPTED',action=requested['action']))
        write_json(state_path,state)
        # Keep the SAME lifetime lock held until server/TTS teardown AND
        # the optional explicit same-owner model release have completed.
        server.shutdown();server_thread.join(timeout=5.);server.server_close();server=None
        models.close();models=None
        if release:state['model_release']=release_owned_model(state)
        state.update(status='CLOSED',closed_utc=utc(),server_closed=True,
            owned_tts_closed=not backend.voice.health()['alive'],
            fixed_daemon_stopped=False,unrelated_models_stopped=False,
            stop_reason=requested['action'])
        write_json(state_path,state)
    except BaseException as error:
        if isinstance(error,InterruptedError) and startup_cancel.is_set():
            state.update(status='CLOSED',stop_reason='explicit_startup_cancel',closed_utc=utc())
        else:
            state.update(status='FAILED',**safe_error(error));result_code=1
    finally:
        watch_done.set();watcher.join(timeout=.5)
        if server is not None:
            if server_thread and server_thread.is_alive():server.shutdown();server_thread.join(timeout=5.)
            server.server_close()
        if models is not None:models.close()
        elif backend is not None:backend.close()
        state['updated_utc']=utc();state['server_closed']=True
        if backend is not None:state['owned_tts_closed']=not backend.voice.health()['alive']
        write_json(state_path,state)
        if lock is not None:lock.release()
    return result_code


if __name__=='__main__':sys.exit(main())
