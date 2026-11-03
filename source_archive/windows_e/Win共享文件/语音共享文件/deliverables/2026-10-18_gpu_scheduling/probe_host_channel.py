"""Time actual ASR/27B/OmniVoice over the existing streaming HTTP route; no playback."""
import argparse
import hashlib
import http.client
import json
from pathlib import Path
import sys
import time
import uuid
import wave

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from common.asr_wire import encode_context
from common.voice_channel import ChannelState,read_frame

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True)
    parser.add_argument('--rounds',type=int,default=1)
    parser.add_argument('--inputs',nargs='+',default=['chat_input.wav','math_input.wav'])
    args=parser.parse_args()
    report={'actual_models':True,'actual_playback':False,'cases':[],'variant':args.name}
    for index in range(args.rounds):
        for name in args.inputs:
            with wave.open(str(ROOT/'deliverables/2026-10-18_stream_playback'/name),'rb') as audio:
                assert (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())==(16000,1,2)
                pcm=audio.readframes(audio.getnframes())
            meta={'protocol':'aura-asr-1','board_boot_id':'host-benchmark','session_id':uuid.uuid4().hex,
                  'request_id':uuid.uuid4().hex,'capture_id':'synthetic-'+uuid.uuid4().hex,'generation':1,
                  'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
            connection=http.client.HTTPConnection('192.168.50.1',8792,timeout=125)
            state=ChannelState(meta);events=[];record={'input':name,'round':index};samples=bytearray()
            started=time.perf_counter()
            try:
                # Baseline and optimized share the same feature/route. Math still
                # uses native thinking; waiting cues never count as answer PCM.
                connection.request('POST','/v1/voice/channel',pcm,{'Content-Type':'application/octet-stream',
                    'X-Aura-Asr':encode_context(meta),'X-Aura-Features':'thinking-feedback-v1'})
                response=connection.getresponse()
                if response.status!=200:raise RuntimeError(response.read(2000).decode())
                while not state.ended:
                    header,raw=read_frame(response);state.accept(header,raw)
                    elapsed=round((time.perf_counter()-started)*1000,2);kind=header['kind']
                    if kind=='error':raise RuntimeError(header['error'])
                    if kind=='start':record['start']=header
                    if kind=='transcript':record.update(transcript=header['text'],transcript_event=header)
                    if kind=='text' and 'request_to_first_text_ms' not in record:record['request_to_first_text_ms']=elapsed
                    if kind=='thinking':record['request_to_hint_event_ms']=elapsed
                    if kind=='audio':
                        if 'request_to_first_pcm_ms' not in record:record['request_to_first_pcm_ms']=elapsed
                        samples.extend(raw)
                    if kind=='end':record['end']=header
                response.read(1)
            finally:connection.close()
            record.update(reply=state.text,elapsed_ms=round((time.perf_counter()-started)*1000,2),
                          samples=state.samples,playback_ack_sent=False)
            output=HERE/(args.name+'-'+str(index)+'-'+name)
            with wave.open(str(output),'wb') as audio:audio.setparams((1,2,24000,0,'NONE','not compressed'));audio.writeframes(samples)
            record['wav']=str(output);report['cases'].append(record)
            (HERE/(args.name+'_host.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(record,ensure_ascii=True),flush=True)

if __name__=='__main__':main()
