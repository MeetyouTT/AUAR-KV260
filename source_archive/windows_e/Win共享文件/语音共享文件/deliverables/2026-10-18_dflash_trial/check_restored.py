"""Verify original services, untouched accepted sources and a real 27B reply."""
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from tools.dialogue_stream import OllamaReplyStream
from board_ssh import ssh


def get(url):
    with urllib.request.urlopen(url,timeout=4) as response:return json.load(response)


report={'status':'WAITING_FOR_ORIGINAL_RESTORE','actual_board_playback':False}
try:
    started=time.monotonic()
    while time.monotonic()-started<600:
        try:
            report['host']=get('http://192.168.50.1:8792/health')
            if report['host'].get('ready'):break
        except OSError:pass
        time.sleep(2)
    else:raise TimeoutError('Original host did not become ready')
    assert report['host']['llm_model']=='aura-qwen3.8-27b-abliterated:iq4_xs'
    assert report['host']['num_step']==16 and not report['host']['busy']
    report['asr']=get('http://192.168.50.1:8791/health')
    assert report['asr']['ready']
    report['accepted_source_comparison']={}
    with zipfile.ZipFile(ROOT/'deliverables/2026-10-18_gpu_scheduling/verified_source.zip') as archive:
        for name in archive.namelist():
            if not name.startswith('aura/') or name.endswith('/'):continue
            path=ROOT/name
            current=hashlib.sha256(path.read_bytes()).hexdigest()
            expected=hashlib.sha256(archive.read(name)).hexdigest()
            row={'sha256':current,'unchanged':current==expected}
            if name=='aura/config/model_storage.local.json' and current!=expected:
                before=json.loads(archive.read(name).decode('utf-8-sig'))
                after=json.loads(path.read_text(encoding='utf-8-sig'))
                row['approved_external_draft_path_only']=(set(after)-set(before)=={'draft_directory'} and all(after[k]==v for k,v in before.items()) and Path(after['draft_directory']).resolve()==Path('D:/AIModels/dflash2-qwen3.8-27b').resolve())
            report['accepted_source_comparison'][name]=row
    assert all(row['unchanged'] or row.get('approved_external_draft_path_only') for row in report['accepted_source_comparison'].values())
    script='''import json,pathlib,urllib.request
s=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
c=json.load(urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=4))
print(json.dumps({'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'camera':c,'phase':s.get('phase'),'playing':s.get('playing'),'recording':s.get('local_recording',{}).get('state')}))
'''
    report['board']=json.loads(ssh('python3 -',script))
    assert report['board']['boot_id']=='94bbc908-4eb8-4111-9435-db2eb1e5a511'
    assert report['board']['camera']['role']=='DPU_YOLOX_PERSON_PREVIEW'
    assert report['board']['camera']['detector']['arch_fingerprint']=='0x101000056010407'
    assert not report['board']['camera']['camera_error'] and not report['board']['camera']['detector_error']
    assert report['board']['camera']['capture_age_ms']<3000
    stream=OllamaReplyStream('http://127.0.0.1:11435','aura-qwen3.8-27b-abliterated:iq4_xs',[],'你好汐蓝，测试结束了，陪我聊聊',90,reply_first=True,compact_grammar=True)
    for kind,value in stream:
        if kind=='complete':report['real_reply']=value
    report['llm_metrics']=stream.metrics
    assert report['real_reply']['reply_text'].strip()
    report['status']='ORIGINAL_RESTORED_RUNTIME_UNCHANGED_EXTERNAL_DRAFT_PATH_RECORDED_REAL_27B_REPLY_PASS'
except BaseException as exc:
    report.update(status='RESTORE_VERIFICATION_FAILED',error=type(exc).__name__+': '+str(exc))
    raise
finally:
    (HERE/'restored.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True),flush=True)
