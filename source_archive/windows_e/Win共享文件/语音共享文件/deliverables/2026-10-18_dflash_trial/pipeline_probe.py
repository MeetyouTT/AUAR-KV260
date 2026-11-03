"""Test-only adapter: existing validated channel + isolated candidate + original TTS16."""
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import time
from unittest.mock import patch
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from tools import native_grammar
from tools.selected_voice_service import VoiceWorker
from tools.voice_channel_source import channel_frames
from common.voice_channel import read_frame,ChannelState
from probe_dflash import api,BASE,MODEL


def experimental_prepare(host,body,timeout,cancelled):
    if cancelled.is_set():raise InterruptedError('Cancelled')
    assert host=='http://127.0.0.1:11435' and not body.get('think')
    prompt=api('/apply-template',{'messages':body['messages'],'chat_template_kwargs':{'enable_thinking':False},'enable_thinking':False,'add_generation_prompt':True})['prompt']
    request={'prompt':prompt,'stream':True,'n_predict':body['options']['num_predict'],'temperature':body['options']['temperature'],'top_k':20,'top_p':.95,'min_p':0.,'repeat_penalty':1.,'seed':42,'cache_prompt':True,'n_keep':4,'grammar':native_grammar.GRAMMAR}
    return BASE,request,{'backend':'isolated_dflash_trial','native_build':native_grammar.VERIFIED_BUILD}


def run(variant):
    report={'variant':variant,'actual_tts':True,'actual_27b':True,'actual_playback':False,'steps':16,'voice_reference_unchanged':True,'cases':[]}
    worker=VoiceWorker(HERE/('tts-'+variant+'-'+uuid.uuid4().hex[:8]),python=sys.executable,model_path=ROOT/'aura/models/tts/OmniVoice',engine='omnivoice')
    try:
        worker.warmup()
        if not worker.ready:raise RuntimeError(worker.error)
        with patch.object(native_grammar,'prepare',experimental_prepare):
            for text in ('今天比较开心，陪我聊聊','今天有点累，想和你说说话'):
                # Fresh cache directory per run prevents repeated answers from being counted as TTS speedup.
                assert not list(worker.cache.glob('*.wav')) or len(report['cases'])==1
                models=SimpleNamespace(voice=worker,histories={},latency_options={'reply_first':True,'early_sentence':True,'coalesce_chat':True,'reuse_history':True,'compact_grammar':True})
                meta={'protocol':'aura-asr-1','board_boot_id':'isolated-dflash-trial','session_id':uuid.uuid4().hex,'request_id':uuid.uuid4().hex,'capture_id':'trial-'+uuid.uuid4().hex,'generation':1,'sample_count':3200,'pcm_sha256':hashlib.sha256(b'\x01\x00'*3200).hexdigest(),'budget_ms':120000}
                state=ChannelState(meta)
                started=time.perf_counter()
                row={'input':text}
                pcm=bytearray()
                for frame in channel_frames(models,meta,text,120,model=MODEL,host='http://127.0.0.1:11435'):
                    header,data=read_frame(io.BytesIO(frame));state.accept(header,data)
                    if header['kind']=='error':raise RuntimeError(header['error'])
                    if header['kind']=='audio':
                        row.setdefault('first_pcm_ms',round((time.perf_counter()-started)*1000,2));pcm.extend(data)
                    if header['kind']=='end':row['end']=header
                assert state.ended and row['end']['tts_cache_hits']==0
                row.update(reply=state.text,pcm_sha256=hashlib.sha256(pcm).hexdigest(),total_ms=round((time.perf_counter()-started)*1000,2))
                report['cases'].append(row)
                (HERE/('pipeline-'+variant+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                print(json.dumps(row,ensure_ascii=True),flush=True)
    except BaseException as exc:
        report['error']=type(exc).__name__+': '+str(exc)
        (HERE/('pipeline-'+variant+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        raise
    finally:
        # Windows venv python.exe may proxy to a child interpreter. Closing stdin
        # lets that owned worker exit and release CUDA before stopping the proxy.
        if worker.process is not None and worker.process.poll() is None:
            try:
                worker.process.stdin.close()
                worker.process.wait(timeout=12)
            except (OSError,TimeoutError):pass
            except Exception:
                import subprocess
                subprocess.run(['taskkill','/PID',str(worker.process.pid),'/T','/F'],capture_output=True,timeout=10)
        worker.close()


if __name__=='__main__':run(sys.argv[1])
