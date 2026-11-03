"""Same target and same TTS16: resident versus idle CPU parking, actual channel ABBA."""
import hashlib
import io
import json
from pathlib import Path
import statistics
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from board.runtime.audio.omnivoice_voice import OmniVoiceSynthesizer
from tools import native_grammar
from tools.voice_channel_source import channel_frames
from common.voice_channel import read_frame,ChannelState
from pipeline_probe import experimental_prepare
import probe_dflash
probe_dflash.REPORT_PATH=HERE/'memory_runner.json'

REPORT={'status':'RUNNING','actual_27b':True,'actual_tts':True,'actual_playback':False,'parameters_unchanged':True,'cases':[]}
RESULT_PATH=HERE/'memory_schedule.json'
MODES=('resident','parked','parked','resident')
RUN_INDEX=6
INPUTS=('今天比较开心，陪我聊聊','今天有点累，想和你说说话')


def save():
    RESULT_PATH.write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')


class DirectVoice:
    def __init__(self,synth):
        self.synth=synth;self.park_idle=False;self.trim_idle=False;self.parked=False;self.metrics={}

    def activate(self):
        if not self.parked:return
        import torch
        start=time.perf_counter()
        self.synth.model.to('cuda:0');torch.cuda.synchronize()
        self.parked=False
        self.metrics['activate_ms']=round((time.perf_counter()-start)*1000,2)

    def configure(self,mode):
        self.park_idle=mode=='parked'
        self.trim_idle=mode=='trimmed'
        if self.park_idle:self.park()
        else:self.activate()
        if self.trim_idle:self.trim()

    def park(self):
        if self.parked:return
        import torch
        start=time.perf_counter()
        torch.cuda.synchronize();self.synth.model.to('cpu');torch.cuda.empty_cache()
        self.parked=True
        self.metrics['park_ms']=round((time.perf_counter()-start)*1000,2)
        self.metrics['torch_allocated_after_park_mb']=round(torch.cuda.memory_allocated()/2**20,2)

    def generate(self,text):
        self.metrics={}
        self.activate()
        try:return self.synth.synthesize(text)
        finally:
            if self.park_idle:self.park()
            elif self.trim_idle:self.trim()

    def trim(self):
        import torch
        start=time.perf_counter()
        before=torch.cuda.memory_reserved()
        torch.cuda.empty_cache()
        self.metrics.update(trim_ms=round((time.perf_counter()-start)*1000,2),reserved_before_mb=round(before/2**20,2),reserved_after_mb=round(torch.cuda.memory_reserved()/2**20,2),allocated_mb=round(torch.cuda.memory_allocated()/2**20,2))


VOICE_CLASS=DirectVoice


def main():
    process,log=probe_dflash.launch('baseline',RUN_INDEX)
    try:
        import torch
        synth=OmniVoiceSynthesizer(HERE/('memory-audio-'+uuid.uuid4().hex[:8]),ROOT/'aura/models/tts/OmniVoice')
        synth.load()
        torch.manual_seed(8701)
        with torch.inference_mode():synth.generate_waves('嗯，我在呢。')
        torch.cuda.synchronize()
        voice=VOICE_CLASS(synth)
        REPORT['gpu_resident']=probe_dflash.gpu()
        with patch.object(native_grammar,'prepare',experimental_prepare):
            for index,mode in enumerate(MODES):
                voice.configure(mode)
                for text in INPUTS:
                    cache=HERE/f'memory-audio-{index}-{len(REPORT["cases"])}-{uuid.uuid4().hex[:6]}'
                    cache.mkdir();synth.cache_root=cache
                    models=SimpleNamespace(voice=voice,histories={},latency_options={'reply_first':True,'early_sentence':True,'coalesce_chat':True,'reuse_history':True,'compact_grammar':True})
                    meta={'protocol':'aura-asr-1','board_boot_id':'memory-schedule-trial','session_id':uuid.uuid4().hex,'request_id':uuid.uuid4().hex,'capture_id':'trial-'+uuid.uuid4().hex,'generation':1,'sample_count':3200,'pcm_sha256':hashlib.sha256(b'\x01\x00'*3200).hexdigest(),'budget_ms':120000}
                    state=ChannelState(meta);pcm=bytearray();row={'mode':mode,'input':text,'repeat':index,'gpu_before':probe_dflash.gpu()}
                    started=time.perf_counter()
                    for frame in channel_frames(models,meta,text,120,model=probe_dflash.MODEL,host='http://127.0.0.1:11435'):
                        header,data=read_frame(io.BytesIO(frame));state.accept(header,data)
                        if header['kind']=='error':raise RuntimeError(header['error'])
                        if header['kind']=='audio':
                            row.setdefault('first_pcm_ms',round((time.perf_counter()-started)*1000,2));pcm.extend(data)
                        if header['kind']=='end':row['end']=header
                    assert state.ended and row['end']['tts_cache_hits']==0 and row['end']['clauses']==1
                    row.update(reply=state.text,pcm_sha256=hashlib.sha256(pcm).hexdigest(),total_ms=round((time.perf_counter()-started)*1000,2),voice_metrics=dict(voice.metrics),gpu_after=probe_dflash.gpu())
                    REPORT['cases'].append(row);save()
                    print(json.dumps({k:row[k] for k in ('mode','input','reply','first_pcm_ms','voice_metrics','gpu_before','gpu_after')},ensure_ascii=True),flush=True)
        REPORT['summary']={mode:{'n':len(rows),'first_pcm_median_ms':statistics.median(r['first_pcm_ms'] for r in rows)} for mode in sorted(set(MODES)) for rows in [[r for r in REPORT['cases'] if r['mode']==mode]]}
        REPORT['audio_parity']={text:len({r['pcm_sha256'] for r in REPORT['cases'] if r['input']==text})==1 for text in sorted({r['input'] for r in REPORT['cases']})}
        REPORT['reply_parity']={text:len({r['reply'] for r in REPORT['cases'] if r['input']==text})==1 for text in sorted({r['input'] for r in REPORT['cases']})}
        REPORT['status']='COMPLETE_NOT_DEPLOYED';save()
        print(json.dumps({k:REPORT[k] for k in ('summary','audio_parity','reply_parity')},ensure_ascii=True),flush=True)
    finally:
        process.terminate()
        try:process.wait(timeout=15)
        except Exception:process.kill()
        log.close()


if __name__=='__main__':
    try:main()
    except BaseException as exc:
        REPORT.update(status='FAILED_NOT_DEPLOYED',error=type(exc).__name__+': '+str(exc));save();raise
