"""Real local 27B contract and multi-turn benchmark, while preserving voice service."""
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools import dialogue_host_ollama as dialogue

STORAGE=json.loads((ROOT/'aura/config/model_storage.local.json').read_text(encoding='utf-8-sig'))
CONFIG=json.loads((Path(STORAGE['weights_directory'])/'candidate_config.json').read_text())
MODEL=CONFIG['model']
HOST=CONFIG['ollama_host']

def post(host,path,value):
    request=urllib.request.Request(host+path,data=json.dumps(value).encode(),
        headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=240) as response:
        return json.load(response)

def main():
    with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=5) as response:
        if json.load(response).get('busy'):
            raise RuntimeError('Voice service busy; retry after current conversation')
    post('http://127.0.0.1:11434','/api/generate',
         {'model':'huihui_ai/qwen3-abliterated:14b','keep_alive':0})
    report={'model':MODEL,'host':HOST,'status':'RUNNING','tests':[],'historical_audio_only':True}
    history=[]
    try:
        for index,text in enumerate(['你好，我叫小林，今天有点累，陪我聊两句。',
                                     '你还记得我叫什么吗？','用一句话解释为什么天空是蓝色的。']):
            started=time.monotonic()
            reply=dialogue.build_response({'request_id':f'27b-check-{index}', 'transcript':text,
                'scene_state':{'scene_seq':index+1},'allowed_emotions':['neutral','friendly','happy','sad'],
                'allowed_avatar_actions':[]},'ollama',MODEL,history=history,strict=True,fast=True,host=HOST)
            timings=dict(dialogue.LAST_TIMINGS)
            if timings.get('model')!=MODEL:
                raise RuntimeError('Unexpected model identity')
            if index==1 and '小林' not in reply['reply_text']:
                raise RuntimeError('Candidate failed the actual multi-turn name recall test')
            report['tests'].append({'prompt':text,'response':reply,'elapsed_seconds':round(time.monotonic()-started,3),
                                    'timings':timings})
            history.extend([{'role':'user','content':text},{'role':'assistant','content':reply['reply_text']}])
        with urllib.request.urlopen(HOST+'/api/ps',timeout=5) as response:
            report['loaded_models']=json.load(response)
        report['gpu']=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,memory.used,memory.free',
                                               '--format=csv'],text=True)
        report['status']='PASS_ACTUAL_27B_CONTRACT_MULTITURN'
    except Exception as exc:
        report.update(status='FAILED',error=f'{type(exc).__name__}: {exc}')
        post(HOST,'/api/generate',{'model':MODEL,'keep_alive':0})
        post('http://127.0.0.1:11434','/api/generate',{'model':'huihui_ai/qwen3-abliterated:14b',
            'keep_alive':'30m','options':{'num_ctx':2048}})
        raise
    finally:
        (HERE/'model_27b_candidate_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))

if __name__=='__main__':
    main()
