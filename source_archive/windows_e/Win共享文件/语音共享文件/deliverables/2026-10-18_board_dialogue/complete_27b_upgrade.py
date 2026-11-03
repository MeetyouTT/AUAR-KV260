"""Finish the authorized local 27B upgrade after download; restore 14B on failure."""
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time
import urllib.request

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
STORAGE=json.loads((ROOT/'aura/config/model_storage.local.json').read_text(encoding='utf-8-sig'))
WEIGHTS=Path(STORAGE['weights_directory'])
CONFIG=ROOT/'aura/config/board_dialogue_model.json'
STATE=HERE/'model_27b_upgrade_status.json'
MODEL='aura-qwen3.8-27b-abliterated:iq4_xs'
HOST='http://127.0.0.1:11435'
VOICE_PYTHON=json.loads((ROOT/'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json').read_text(encoding='utf-8-sig'))['voice']['python']

def status(stage,**extra):
    value={'stage':stage,'model':MODEL,'preference':'27B quality over latency',**extra}
    temp=STATE.with_suffix('.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    temp.replace(STATE)
    print(json.dumps(value,ensure_ascii=True),flush=True)

def health():
    try:
        with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=3) as response:
            return json.load(response)
    except OSError:
        return {}

def post(host,value):
    request=urllib.request.Request(host+'/api/generate',data=json.dumps(value).encode(),
                                   headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=240) as response:
        return json.load(response)

def restart_voice():
    for _ in range(120):
        if not health().get('busy'):
            break
        time.sleep(1)
    else:
        raise RuntimeError('Voice service remains busy; restart deferred')
    # Only this project's board_model_host and its descendants are stopped.
    command=r"""
    $all=Get-CimInstance Win32_Process
    $targets=@($all | Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -like '*E:\Win共享文件\语音共享文件\aura\tools\board_model_host.py*'})
    $ids=@($targets | ForEach-Object {$_.ProcessId})
    do {
        $children=@($all | Where-Object {$_.ParentProcessId -in $ids -and $_.ProcessId -notin $ids})
        $ids+=@($children | ForEach-Object {$_.ProcessId})
    } while ($children.Count)
    [array]::Reverse($ids)
    foreach ($idToStop in $ids) {Stop-Process -Id $idToStop -Force -ErrorAction SilentlyContinue}
    $project='E:\Win共享文件\语音共享文件'
    $voiceConfig=Get-Content -LiteralPath (Join-Path $project 'deliverables/2026-10-11_omnivoice_dialogue/stage_config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $voicePython=[string]$voiceConfig.voice.python
    $launcher=Join-Path $project 'deliverables/2026-10-18_board_dialogue/launch_models.py'
    $startup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0}
    $launchCommand='"'+$voicePython+'" -B "'+$launcher+'" --voice-python "'+$voicePython+'"'
    $launched=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$launchCommand;CurrentDirectory=$project;ProcessStartupInformation=$startup}
    if ($launched.ReturnValue -ne 0) {throw ('Model startup failed: '+$launched.ReturnValue)}
    """
    subprocess.run(['powershell.exe','-NoProfile','-Command',command],check=True,timeout=60)
    expected=json.loads(CONFIG.read_text(encoding='utf-8-sig'))['model']
    for _ in range(600):
        value=health()
        if value.get('ready') and value.get('llm_model')==expected:
            return value
        time.sleep(1)
    raise RuntimeError('Voice service failed to become ready with expected model')

def main():
    backup=CONFIG.read_bytes()
    switched=False
    try:
        status('DOWNLOADING',active_model=json.loads(backup.decode('utf-8-sig'))['model'])
        deadline=time.monotonic()+12*3600
        verified=WEIGHTS/'download_verified.json'
        while not verified.is_file():
            if (WEIGHTS/'download_failed.txt').is_file():
                raise RuntimeError((WEIGHTS/'download_failed.txt').read_text(encoding='utf-8'))
            if time.monotonic()>deadline:
                raise TimeoutError('Weight download has not completed within 12 hours')
            time.sleep(10)
        meta=json.loads((WEIGHTS/'download_manifest.json').read_text(encoding='utf-8-sig'))
        weight=WEIGHTS/meta['path']
        status('VERIFYING_WEIGHT')
        digest=hashlib.sha256()
        with weight.open('rb') as source:
            while block:=source.read(8*1024*1024):
                digest.update(block)
        if weight.stat().st_size!=meta['size'] or digest.hexdigest()!=meta['lfs']['oid']:
            raise RuntimeError('Weight file failed final SHA256/length verification')
        from project_ollama import ensure
        ensure()
        blob=Path(STORAGE['ollama_directory'])/'blobs'/('sha256-'+digest.hexdigest())
        blob.parent.mkdir(parents=True,exist_ok=True)
        if not blob.exists():
            os.link(weight,blob)
        status('IMPORTING_VERIFIED_MODEL')
        env=dict(os.environ,OLLAMA_HOST='127.0.0.1:11435')
        with (HERE/'model_27b_import.log').open('w',encoding='utf-8') as log:
            subprocess.run(['ollama','create',MODEL,'-f',str(WEIGHTS/'Modelfile')],env=env,
                           stdout=log,stderr=log,check=True,timeout=900)
        status('TESTING_CANDIDATE')
        runpy.run_path(str(HERE/'verify_candidate_27b.py'),run_name='__main__')
        (HERE/'model_config_before_27b.json').write_bytes(backup)
        CONFIG.write_bytes((WEIGHTS/'candidate_config.json').read_bytes())
        switched=True
        # Free the candidate cache during the voice engine's cold initialization.
        post(HOST,{'model':MODEL,'keep_alive':0})
        status('RESTARTING_VOICE_WITH_27B')
        current=restart_voice()
        status('TESTING_FULL_VOICE_HTTP',health=current)
        runpy.run_path(str(HERE/'verify_model_27b.py'),run_name='__main__')
        report=json.loads((HERE/'model_27b_verification.json').read_text(encoding='utf-8'))
        if report['response']['voice_reply']['llm_model']!=MODEL:
            raise RuntimeError('Full voice response used an unexpected model')
        note=('> **Qwen3.8 27B模型升级已验证：** 当前8792实际使用 `'+MODEL+
              '`（Huihui破甲版UD-IQ4_XS），本机独立Ollama端口11435；权重SHA256已核验，真实多轮合同和历史录音完整语音HTTP验证通过。'
              '本轮未新增板端实录听音验收。证据：`deliverables/2026-10-18_board_dialogue/model_27b_verification.json`。\n\n')
        for doc in (ROOT/'README.md',HERE/'README.md'):
            doc.write_text(note+doc.read_text(encoding='utf-8-sig'),encoding='utf-8')
        (WEIGHTS/'README.md').write_text(note+'\n大语言模型权重及下载缓存位于项目外的本地 D:/AIModels；项目只保存代码、路径配置和验证记录。\n',encoding='utf-8')
        status('PASS_27B_ACTIVE_VOICE_VERIFIED',health=current,
               http_seconds=report['elapsed_seconds'],new_board_recording_verified=False)
    except Exception as exc:
        failure=f'{type(exc).__name__}: {exc}'
        status('FAILED',error=failure)
        if switched:
            CONFIG.write_bytes(backup)
            try:
                post(HOST,{'model':MODEL,'keep_alive':0})
                restored=restart_voice()
                status('FAILED_RESTORED_PREVIOUS_MODEL',error=failure,health=restored)
            except Exception as restore_error:
                status('FAILED_RESTORE_NEEDS_ATTENTION',error=failure,restore_error=str(restore_error))
        raise

if __name__=='__main__':
    main()
