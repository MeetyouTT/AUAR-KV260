"""On-board real pipeline test, with synthetic input and the actual avatar controller.

Runs in an isolated overlay. Existing GTK and camera services are not restarted.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import uuid
import urllib.request
import wave


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--case',type=Path,action='append',required=True);parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();sys.path.insert(0,str(args.runtime/'aura'))
    from tools.demo_script import create_demo_core
    from tools.gstreamer_audio import GStreamerAudioOutput
    from tools.streaming_controller import StreamingController
    from tools.board_recording import RecordingController
    from tools.selected_voice_service import SpeechJobs,VoiceWorker
    from board.runtime.audio.channel_jobs import ChannelConversationJobs
    from board.runtime.audio.capture import CapturedAudio,FORMAT
    from host.model_service.protocol import AudioRef
    def check_idle():
        u=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3))
        if u['phase']!='IDLE' or u['playing'] or u.get('local_recording',{}).get('state')=='RECORDING' or u.get('local_transcription',{}).get('service',{}).get('pending'):
            raise RuntimeError('User interaction detected; isolated test stopped')
    check_idle()
    cache=args.report.parent/'integration-cache';cache.mkdir(parents=True,exist_ok=True)
    config=json.loads((args.runtime/'avatar_conversation_settings.json').read_text())
    output=GStreamerAudioOutput(args.report.parent/'integration-audio.log',persistent=True)
    jobs=SpeechJobs(cache,VoiceWorker(cache,cached_only=True))
    transcriber=ChannelConversationJobs(config,Path('/proc/sys/kernel/random/boot_id').read_text().strip(),cache/'cache')
    inner=StreamingController(create_demo_core('reuse'),jobs,output)
    owner=RecordingController(inner,transcriber=transcriber)
    report={'status':'RUNNING','input_kind':'WINDOWS_SAPI_SYNTHETIC_NOT_USER_CAPTURE','actual_playback':True,
            'acoustic_onset_measured':False,'existing_services_modified':False,'cases':[]}
    try:
        for case in args.case:
            check_idle()
            with wave.open(str(case),'rb') as audio:
                if (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())!=(16000,1,2):raise ValueError('Wrong test recording format')
                pcm=audio.readframes(audio.getnframes())
            count=len(pcm)//2
            owner.utterance=CapturedAudio('synthetic-'+uuid.uuid4().hex,AudioRef(1,0,count,FORMAT),pcm,0,round(count/16))
            owner.recording_state='READY';owner._queue_transcription()
            started=time.monotonic();deadline=started+125;last_check=started
            samples=[];max_mouth=0.;phases=set()
            previous_turns=len(inner.turns)
            while time.monotonic()<deadline:
                frame=owner.tick();state=owner.public();audio_state=output.read()
                if state.get('error') or state['local_transcription'].get('error'):
                    raise RuntimeError(state.get('error') or state['local_transcription']['error'])
                if time.monotonic()-last_check>=.2:check_idle();last_check=time.monotonic()
                phases.add(state['phase']);max_mouth=max(max_mouth,float((frame or {}).get('mouth_level',0)))
                if len(samples)<1400:samples.append({'elapsed_ms':round((time.monotonic()-started)*1000,2),
                    'phase':state['phase'],'mouth':float((frame or {}).get('mouth_level',0)),
                    'clock':audio_state.get('clock'),'track':audio_state.get('track'),
                    'audible':audio_state.get('audible'),'answer_clock':audio_state.get('answer_clock')})
                ack=transcriber.last_ack
                if len(inner.turns)>previous_turns and state['local_transcription']['state']=='ANSWERED' and ack and ack.get('request_id')==owner.transcription['request_id']:
                    if not ack.get('committed'):raise RuntimeError(str(ack))
                    break
                time.sleep(.025)
            else:raise RuntimeError('Functional test exceeded turn budget')
            result={'input':str(case),'transcript':owner.transcription['text'],'reply':inner.reply,
                    'turn':inner.turns[-1],'ack':transcriber.last_ack,'phases':sorted(phases),
                    'max_mouth':max_mouth,'elapsed_ms':round((time.monotonic()-started)*1000,2),'samples':samples}
            if max_mouth<=0:raise RuntimeError('No mouth movement during real playback')
            report['cases'].append(result)
            args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2))
        report['status']='PASS_REAL_PLAYBACK_AND_HISTORY_ACK_REQUIRES_LISTENING'
    except Exception as exc:
        report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
        raise
    finally:
        owner.close();output.close();jobs.close()
        args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='cases'}))


if __name__=='__main__':main()
