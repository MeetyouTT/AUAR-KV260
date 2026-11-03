"""Owned candidate subprocesses; always close them before returning to wrapper."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

BASE=Path(__file__).resolve().parent
HERE=Path(os.environ.get('AURA_TTS_TRIAL_DIR',str(BASE)))
HERE.mkdir(parents=True,exist_ok=True)
ROOT=BASE.parents[1]
RUNTIME=Path(os.environ.get('AURA_TTS_RUNTIME',str(BASE/'runtime')))
BACKEND=os.environ.get('AURA_TTS_BACKEND','Vulkan0')
MODELS=Path('D:/AIModels/cosyvoice3-streaming-validation')

def get(path):
    with urllib.request.urlopen('http://127.0.0.1:51889'+path,timeout=4) as r:return json.load(r)

def main():
    before=json.loads((BASE/'before.json').read_text(encoding='utf-8'))
    manifest=json.loads((BASE/'download.json').read_text(encoding='utf-8'))
    assert manifest['status']=='VERIFIED'
    assert hashlib.sha256(Path(before['reference']).read_bytes()).hexdigest()==before['reference_sha256']
    prompt=MODELS/'xilan-reference.gguf'
    with (HERE/'frontend.log').open('w',encoding='utf-8') as log:
        command=[str(RUNTIME/'cosyvoice-cli.exe'),'--frontend-only','--speech-tokenizer',str(MODELS/'frontend-onnx/speech_tokenizer_v3.int8.onnx'),'--campplus',str(MODELS/'frontend-onnx/campplus.int8.onnx'),'--prompt-audio',before['reference'],'--prompt-text',before['reference_text'],'--prompt-speech-output',str(prompt)]
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=180,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    assert prompt.exists() and prompt.stat().st_size>0
    log=(HERE/'server.log').open('w',encoding='utf-8')
    process=None
    try:
        command=[str(RUNTIME/'cosyvoice-server.exe'),'--model',str(MODELS/'CosyVoice3-2512_Q8_0.gguf'),'--voice-prompt','xilan='+str(prompt),'--host','127.0.0.1','--port','51889','--backend',BACKEND,'--max-llm-len','1024','--dit-kv-cache-length','4096','--dit-kv-fixed-slots','1','--inference-buffer-policy','balanced','--threads','4','--seed','8701','--verbose']
        command.extend(json.loads(os.environ.get('AURA_TTS_EXTRA_ARGS','[]')))
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        (HERE/'candidate_process.json').write_text(json.dumps({'pid':process.pid,'command':command}),encoding='utf-8')
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError('Candidate server exited: '+str(process.returncode))
            try:
                status=get('/status')
                if status.get('model_loaded'):break
            except (OSError,ValueError):pass
            time.sleep(.5)
        else:raise TimeoutError('Candidate readiness deadline')
        (HERE/'candidate_status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
        if os.environ.get('AURA_TTS_QUICK_CONTENT')=='1' or os.environ.get('AURA_TTS_PIPELINE_ONLY')=='1':
            expected_flash=os.environ['AURA_TTS_EXPECT_FLASH']=='1'
            # This build promotes the requested F16 V cache to F32. Retain
            # and report that higher precision rather than rejecting it as
            # if it were an unsupported or lower-precision configuration.
            assert status['k_cache_type']=='f16' and status['v_cache_type'] in ('f16','f32') and status['llm_use_flash_attn']==expected_flash and status['flow_use_flash_attn']==expected_flash,status
        print(json.dumps({'status':'CANDIDATE_READY','details':status}),flush=True)
        sys.path.insert(0,str(ROOT/'aura'))
        from tools.dialogue_stream import OllamaReplyStream
        warm=OllamaReplyStream('http://127.0.0.1:11435','aura-qwen3.8-27b-abliterated:iq4_xs',[],'你好',90,reply_first=True,compact_grammar=True)
        list(warm)
        gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,memory.used,utilization.gpu','--format=csv,noheader'],text=True)
        (HERE/'coexistence.json').write_text(json.dumps({'gpu':gpu,'llm_warm_metrics':warm.metrics},indent=2),encoding='utf-8')
        scripts=('check_selected_audio.py','probe_pipeline.py') if os.environ.get('AURA_TTS_PIPELINE_ONLY')=='1' else (('probe_quick_content.py',) if os.environ.get('AURA_TTS_QUICK_CONTENT')=='1' else (('probe_cuda_variants.py',) if os.environ.get('AURA_TTS_VARIANTS')=='1' else ('probe_streaming.py','check_audio.py','probe_pipeline.py')))
        for script in scripts:
            with (HERE/(Path(script).stem+'.log')).open('w',encoding='utf-8') as script_log:
                subprocess.run([sys.executable,'-B','-u',str(BASE/script)],check=True,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW,stdout=script_log,stderr=subprocess.STDOUT)
            if script in ('check_audio.py','check_selected_audio.py'):
                content=json.loads((HERE/'audio_content.json').read_text(encoding='utf-8'))
                if any(case['character_error_rate']>.15 for case in content['cases']):
                    (HERE/'quality_rejected.json').write_text(json.dumps({'status':'CONTENT_SCREEN_REJECTED_NOT_DEPLOYED','reason':'At least one generated clip exceeds 15% ASR character error; pipeline not pursued. Listening still required to identify cause.'},indent=2),encoding='utf-8')
                    break
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
        log.close()

if __name__=='__main__':
    try:main()
    except BaseException as exc:
        (HERE/'failure.json').write_text(json.dumps({'status':'FAILED_NOT_DEPLOYED','error':type(exc).__name__+': '+str(exc)},ensure_ascii=False,indent=2),encoding='utf-8')
        raise
