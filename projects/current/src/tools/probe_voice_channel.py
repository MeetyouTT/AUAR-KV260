"""Receive a real voice channel using a historical recording; no playback.

The optional WAV output is a local capture of received PCM, not a speech model.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import uuid
import wave

AURA=Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path: sys.path.insert(0,str(AURA))
from board.runtime.audio.voice_channel import VoiceChannel


def probe(host, port, wav, *, rounds=1, output=None):
    with wave.open(str(wav),'rb') as audio:
        if (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())!=(16000,1,2):
            raise ValueError('Input must be 16kHz mono PCM16')
        pcm=audio.readframes(audio.getnframes())
    channel=VoiceChannel(host,port)
    session=uuid.uuid4().hex
    reports=[]
    try:
        for turn in range(rounds):
            meta={'protocol':'aura-asr-1','board_boot_id':'historical-channel-probe','session_id':session,
                  'request_id':uuid.uuid4().hex,'generation':turn+1,'capture_id':'historical-recording',
                  'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
            started=time.monotonic()
            report={'historical_recording':True,'actual_playback':False,'first_text_ms':None,
                    'first_pcm_ms':None,'frames':0,'audio_packets':0,'transcript':'','connection_local_port':None}
            captured=bytearray()
            def receive(header,payload):
                elapsed=round((time.monotonic()-started)*1000,2)
                report['frames']+=1
                if report['connection_local_port'] is None:
                    report['connection_local_port']=channel.socket.getsockname()[1]
                if header['kind']=='start':report['host_start']=header
                elif header['kind']=='transcript':report['transcript']=header['text']
                elif header['kind']=='text' and report['first_text_ms'] is None:report['first_text_ms']=elapsed
                elif header['kind']=='audio':
                    if report['first_pcm_ms'] is None:report['first_pcm_ms']=elapsed
                    report['audio_packets']+=1
                    captured.extend(payload)
                elif header['kind']=='end':report['host_end']=header
            report['result']=channel.exchange(meta,pcm,receive)
            report['total_ms']=round((time.monotonic()-started)*1000,2)
            report['received_pcm_sha256']=hashlib.sha256(captured).hexdigest()
            if report['received_pcm_sha256']!=report['result']['pcm_sha256']:
                raise ValueError('Probe PCM digest differs')
            if output:
                target=Path(output).with_name(Path(output).stem+f'-turn{turn+1}.wav')
                target.parent.mkdir(parents=True,exist_ok=True)
                with wave.open(str(target),'wb') as audio:
                    audio.setparams((1,2,24000,0,'NONE','not compressed'))
                    audio.writeframes(captured)
                report['received_wav']=str(target)
            reports.append(report)
    finally:channel.close()
    return {'status':'PASS_CHANNEL_RECEIVE_ONLY','speech_models_on_board':False,'turns':reports,
            'same_tcp_connection':len({r['connection_local_port'] for r in reports})==1}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',default='192.168.50.1')
    parser.add_argument('--port',type=int,default=8792)
    parser.add_argument('--wav',type=Path,required=True)
    parser.add_argument('--rounds',type=int,choices=range(1,4),default=1)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    result=probe(args.host,args.port,args.wav,rounds=args.rounds,output=args.output)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
