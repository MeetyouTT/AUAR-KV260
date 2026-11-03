"""One-time local deployment continuation. Never connects to the board."""
import csv, datetime, hashlib, http.client, json, math, os, shutil, socket, subprocess, sys, time, uuid
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
AURA=ROOT/'aura'
PACKAGE=ROOT.parent/'5090主机迁移包_20261101'
VOICE=Path('D:/AURARuntimes/voice-py310/Scripts/python.exe')
HOST=ROOT/'deliverables/2026-10-30_board_owner/integration/production_model_host'
RUNTIME=ROOT/'deliverables/2026-10-18_board_dialogue/model_host'
MODEL='aura-qwen3.8-27b-abliterated:iq4_xs'
WEIGHTS=Path('D:/AIModels/qwen3.8-27b-abliterated/Huihui-Qwen3.8-27B-abliterated-UD-IQ4_XS.gguf')
EXPECTED='d83adbbbaace8acdfcfe28004f779326176b9df00b4ec99dc6c24d749723d3b9'
START=time.monotonic()
read_context=json.loads((OUT/"CONNECTION_CONTEXT.json").read_bytes()) if (OUT/"CONNECTION_CONTEXT.json").exists() else {}
state=dict(schema='aura-5090-local-deployment-1',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    board_connected=bool(read_context.get('user_reported_cable_connected',False)),board_access_attempted_by_deployer=False,playback_or_motion_performed=False,
    target_endpoint='http://127.0.0.1:8797',model=MODEL,formal_tts='OmniVoice16',complete=False)

def read(p):return json.loads(Path(p).read_bytes())
def write(p,data):
    p=Path(p);temporary=p.with_name(p.name+'.part-'+uuid.uuid4().hex)
    temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(temporary,p)
def status(phase,**extra):
    state.update(phase=phase,updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),**extra)
    if (OUT/'llm_download_progress.json').exists():state['download']=read(OUT/'llm_download_progress.json')
    write(OUT/'STATUS.json',state)
def run(args,log,timeout=600,env=None):
    with (OUT/log).open('wb') as output:
        done=subprocess.run([str(x) for x in args],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,
            timeout=timeout,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
    if done.returncode:raise RuntimeError(f'Command failed: {log}; exit={done.returncode}')
def backup(p):
    p=Path(p);relative=p.relative_to(ROOT);target=OUT/'before'/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    if p.exists() and not target.exists():shutil.copyfile(p,target)
def installers():
    source=r"""[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$installOwners=@(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*AURARuntimes*voice-py310* -m pip *' } | Select-Object -ExpandProperty ProcessId)
ConvertTo-Json -InputObject $installOwners -Compress
"""
    r=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',source],capture_output=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
    if r.returncode:raise RuntimeError('Cannot inspect current runtime installer ownership')
    return json.loads(r.stdout.decode('utf-8-sig'))
def free_endpoint():
    with socket.socket() as s:s.bind(('127.0.0.1',8797))
def http(path,body=None,timeout=130):
    c=http.client.HTTPConnection('127.0.0.1',8797,timeout=timeout)
    try:
        c.request('POST' if body is not None else 'GET',path,json.dumps(body).encode() if body is not None else None,{'Content-Type':'application/json'})
        r=c.getresponse();raw=r.read(4*1024*1024+1)
        if r.status!=200 or len(raw)>4*1024*1024:raise RuntimeError('Local inference HTTP validation failed')
        return json.loads(raw)
    finally:c.close()

def main():
    status('WAITING_FOR_CURRENT_ENVIRONMENT_INSTALL')
    absent_since=None
    while True:
        active=installers()
        if active:absent_since=None
        elif absent_since is None:absent_since=time.monotonic()
        elif time.monotonic()-absent_since>=25:break
        status('WAITING_FOR_CURRENT_ENVIRONMENT_INSTALL',installer_pids=active)
        if time.monotonic()-START>8*3600:raise TimeoutError('Existing installer did not finish within eight hours')
        time.sleep(10)
    status('FINALIZING_ENVIRONMENT',installer_pids=[])
    run([VOICE,'-m','pip','install','--upgrade','--timeout','120','--retries','10','pip==26.2.1'],'pip_upgrade_for_resume.log')
    requirements=OUT/'voice_py310_requirements_5090.txt'
    check="import importlib.metadata as m,json,sys; specs=[x.strip().split('==') for x in open(sys.argv[1],encoding='utf-8-sig') if x.strip() and not x.startswith('#')]; assert all(m.version(n)==v for n,v in specs)"
    result=subprocess.run([str(VOICE),'-I','-B','-c',check,str(requirements)],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        run([VOICE,'-m','pip','install','--progress-bar','off','--timeout','120','--retries','10','--resume-retries','30','--index-url','https://pypi.org/simple',
            '--find-links',PACKAGE/'environment/wheels','-r',OUT/'voice_py310_install_5090.txt'],'environment_background_repair.log',timeout=8*3600)
    run([VOICE,'-m','pip','install','--force-reinstall','--no-deps',PACKAGE/'environment/wheels/omnivoice-0.2.1-py3-none-any.whl'],
        'preserved_omnivoice_install.log')
    run([VOICE,'-m','pip','check'],'pip_check.log')
    run(['powershell.exe','-NoProfile','-NonInteractive','-File',PACKAGE/'environment/Test-5090Host.ps1',
        '-VoicePython',VOICE,'-ProjectRoot',ROOT,'-TinyCudaCheck'],'cuda_environment_validation.log')
    probe="import importlib.metadata as m,json,sys,torch; print(json.dumps(dict(python=sys.version,executable=sys.executable,torch=torch.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(0),compute_capability=torch.cuda.get_device_capability(0),arch_list=torch.cuda.get_arch_list(),packages={n:m.version(n) for n in ['omnivoice','torchaudio','transformers','numpy','soundfile']})))"
    run([VOICE,'-I','-B','-c',probe],'environment_ready.json')
    run([VOICE,'-m','pip','freeze','--all'],'requirements_installed.txt')
    status('ENVIRONMENT_VALIDATED_RUNNING_REGRESSION',environment_validated=True)
    test_env=dict(os.environ,PYTHONPATH=str(AURA),PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    temporary=OUT/('test_work_'+uuid.uuid4().hex)
    assert temporary.resolve().is_relative_to(OUT.resolve()) and not temporary.exists()
    run([VOICE,'-B','-X','utf8','-m','pytest','-q','-p','no:cacheprovider','--basetemp',temporary,
        OUT/'test_host_portability.py',HOST/'test_production_runtime.py',
        AURA/'tests/framework/test_model_inference.py',AURA/'tests/framework/test_model_inference_startup.py'],
        'host_regression_complete.log',env=test_env)
    sys.path[:0]=[str(AURA),str(ROOT/'deliverables/2026-10-18_board_dialogue')]
    from tools.service_instance_lock import ServiceInstanceLock
    from project_ollama import ensure
    free_endpoint()
    status('CALIBRATING_ORIGINAL_OMNIVOICE16')
    with ServiceInstanceLock(RUNTIME/'voice8792.instance.lock'):
        run([VOICE,'-B','-X','utf8',OUT/'measure_models.py','tts'],'tts_calibration_runtime.log')
    tts=read(OUT/'tts_calibration.json')
    if tts.get('passed') is not True:raise RuntimeError('TTS calibration did not pass')
    status('WAITING_FOR_VERIFIED_27B_DOWNLOAD',tts_validated=True)
    while not (OUT/'llm_download_verification.json').exists():
        if (OUT/'llm_download_failure.json').exists():raise RuntimeError('Model downloader failed; inspect llm_download_failure.json')
        if time.monotonic()-START>48*3600:raise TimeoutError('Model download wait exceeded 48 hours; partial data retained')
        status('WAITING_FOR_VERIFIED_27B_DOWNLOAD',tts_validated=True)
        time.sleep(15)
    verification=read(OUT/'llm_download_verification.json')
    if verification.get('status')!='VERIFIED' or verification.get('sha256')!=EXPECTED or WEIGHTS.stat().st_size!=14403496864:
        raise RuntimeError('Original 27B verification is missing or differs')
    status('IMPORTING_AND_CALIBRATING_FIXED_27B',llm_weights_verified=True)
    with ServiceInstanceLock(RUNTIME/'voice8792.instance.lock'):
        daemon=ensure()
        if daemon.get('ready') is not True or daemon.get('needs_controlled_restart'):raise RuntimeError('Project daemon ownership is not ready')
        write(OUT/'project_daemon_verified.json',daemon)
        modelfile=WEIGHTS.parent/'Modelfile'
        content='FROM ./'+WEIGHTS.name+'\nPARAMETER num_ctx 2048\nPARAMETER temperature 0.6\n'
        if modelfile.exists() and modelfile.read_text(encoding='utf-8-sig')!=content:raise RuntimeError('Existing Modelfile differs; no overwrite')
        modelfile.write_bytes(content.encode('utf-8'))
        env=dict(os.environ,OLLAMA_HOST='127.0.0.1:11435',OLLAMA_MODELS='D:/AIModels/Ollama-AURA')
        executable=shutil.which('ollama.exe')
        if not executable:raise RuntimeError('Ollama executable not found')
        run([executable,'create',MODEL,'-f',modelfile],'ollama_model_import.log',timeout=1200,env=env)
        run([VOICE,'-B','-X','utf8',OUT/'measure_models.py','llm'],'llm_calibration_runtime.log')
    llm=read(OUT/'llm_calibration.json')
    if llm.get('passed') is not True:raise RuntimeError('LLM calibration did not pass')
    if tts['gpu_before']['uuid']!=llm['gpu_before']['uuid']:raise RuntimeError('GPU identity changed between measurements')
    gpu_path=AURA/'config/gpu_runtime.local.json';backup(gpu_path)
    policy=dict(mode='adaptive',max_pending=2,max_wait_seconds=5.0,sample_max_age_seconds=.75,
        reserve_mib=1024,llm_extra_mib=llm['candidate_steady_extra_mib'],llm_cold_extra_mib=llm['candidate_cold_extra_mib'],
        tts_extra_mib=tts['candidate_steady_extra_mib'],tts_cold_extra_mib=tts['candidate_cold_extra_mib'],
        gpu_uuid=llm['gpu_before']['uuid'],calibration_id='5090laptop24gb-27biq4xs-ctx2048-ov16-20261102-r1')
    from common.gpu_coordination import GpuPolicy
    GpuPolicy.from_dict(policy)
    write(gpu_path,policy)
    write(OUT/'gpu_calibration.json',dict(status='MEASURED_INDIVIDUALLY_COEXISTENCE_PENDING',policy=policy,
        tts_evidence='tts_calibration.json',llm_evidence='llm_calibration.json',ollama_policy=read(AURA/'config/ollama_runtime.local.json')))
    status('STARTING_LOCAL_MODEL_INFERENCE_SERVICE',gpu_calibrated_individually=True)
    latest=HOST/'latest.json'
    if latest.exists():
        old=read(latest)
        if 'Users\\35870\\' in old.get('owner',{}).get('executable',''):
            backup(latest)
            archived=HOST/'latest.before-5090-20261102.json'
            if archived.exists():raise RuntimeError('Old latest archive already exists; inspect before replacing any owner')
            latest.replace(archived)
        else:raise RuntimeError('Another model service owner record exists; no takeover attempted')
    run([VOICE,'-B','-X','utf8',HOST/'manage.py','start'],'model_service_start.json',timeout=340)
    status('VERIFYING_LOCAL_MODEL_HTTP_AND_FRESH_PCM')
    health=http('/health',timeout=5)
    if health.get('role')!='model_inference_only' or health.get('backend',{}).get('tts_ready') is not True:
        raise RuntimeError('Local model service health not ready')
    from common.model_inference_wire import Owner,validate_response,decode_audio
    owner=dict(board_boot_id='public-5090-deployment',session_id='public-'+uuid.uuid4().hex,generation=1)
    llm_request=dict(protocol_version=1,request_id='public-llm-'+uuid.uuid4().hex,budget_ms=120000,**owner,
        task='dialogue',messages=[{'role':'system','content':'这是公开部署验证，请简短回答。'},{'role':'user','content':'请说你已准备好了。'}])
    response=http('/v1/inference/llm',llm_request)
    validate_response(response,Owner.from_dict(llm_request),'llm')
    if response.get('ok') is not True or not response['result']['text']:raise RuntimeError('Local LLM response invalid')
    llm_result=dict(request_id=llm_request['request_id'],characters=len(response['result']['text']))
    tts_request=dict(protocol_version=1,request_id='public-tts-'+uuid.uuid4().hex,budget_ms=120000,**owner,text='你好，本机部署验证完成。')
    response=http('/v1/inference/tts',tts_request)
    validate_response(response,Owner.from_dict(tts_request),'tts')
    if response.get('ok') is not True:raise RuntimeError('Local TTS response invalid')
    pcm,rate=decode_audio(response['result']['audio'])
    if rate!=24000 or not any(pcm):raise RuntimeError('Fresh local PCM invalid')
    tts_result=dict(request_id=tts_request['request_id'],samples=len(pcm)//2,sample_rate=rate,sha256=hashlib.sha256(pcm).hexdigest())
    pcm=response=None
    health=http('/health',timeout=5)
    ready=dict(status='READY_LOCAL_ONLY_BOARD_INTEGRATION_PENDING',endpoint='http://127.0.0.1:8797',model=MODEL,
        weights_sha256=EXPECTED,tts='Original OmniVoice16 and accepted reference',health=health,
        llm_public_probe=llm_result,tts_public_probe=tts_result,board_accessed_by_deployer=False,audio_played=False,
        business_database_opened=False,physical_or_board_acceptance=False,completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write(OUT/'READY_LOCAL.json',ready)
    calibration=read(OUT/'gpu_calibration.json');calibration['status']='VALIDATED_LOCAL_BOTH_RESIDENT_PUBLIC_HTTP'
    calibration['limits']='Individual phases, shared residency and bounded public requests; no board, physical playback or sustained stress acceptance'
    write(OUT/'gpu_calibration.json',calibration)
    run([VOICE,'-B','-X','utf8',HOST/'manage.py','status'],'model_service_status.json')
    source_paths=[ROOT/'start_model_dashboard.ps1',AURA/'config/model_inference.local.json',gpu_path,
        AURA/'config/ollama_runtime.local.json',HOST/'production_runtime.py',HOST/'manage.py',
        ROOT/'deliverables/2026-10-18_board_dialogue/board_ssh.py']
    write(OUT/'source_manifest_5090.json',[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in source_paths])
    status('READY_LOCAL_ONLY_BOARD_INTEGRATION_PENDING',complete=True,environment_validated=True,tts_validated=True,
        llm_weights_verified=True,gpu_calibrated_individually=True,local_http_verified=True,ready_receipt='READY_LOCAL.json')

if __name__=='__main__':
    try:main()
    except BaseException as error:
        status('FAILED',failed_phase=state.get('phase'),error_type=type(error).__name__,error=str(error),complete=False)
        raise
