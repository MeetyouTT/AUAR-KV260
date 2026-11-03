"""Cancel actual cached feedback and actual answer playback without committing history."""
import argparse
import json
from pathlib import Path
import sys
import time
import urllib.request
import uuid
import wave


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',type=Path,required=True)
    args=parser.parse_args();stage=args.stage;sys.path.insert(0,str(stage/'runtime/aura'))
    from tools.demo_script import create_demo_core
    from tools.gstreamer_audio import GStreamerAudioOutput
    from tools.streaming_controller import StreamingController
    from tools.board_recording import RecordingController
    from tools.selected_voice_service import SpeechJobs,VoiceWorker
    from board.runtime.audio.channel_jobs import ChannelConversationJobs
    from board.runtime.audio.capture import CapturedAudio,FORMAT
    from host.model_service.protocol import AudioRef
    def get(url):
        with urllib.request.urlopen(url,timeout=3) as response:return json.load(response)
    def check_idle():
        state=get('http://127.0.0.1:8783/api/state')
        if state['phase']!='IDLE' or state['playing'] or state.get('local_recording',{}).get('state')=='RECORDING':
            raise RuntimeError('User interaction detected; test stopped')
    check_idle()
    cache=stage/'cancel-cache';cache.mkdir(exist_ok=True)
    config=json.loads((stage/'runtime/avatar_conversation_settings.json').read_text())
    output=GStreamerAudioOutput(stage/'cancellation-audio.log',persistent=True)
    jobs=SpeechJobs(cache,VoiceWorker(cache,cached_only=True))
    transcriber=ChannelConversationJobs(config,Path('/proc/sys/kernel/random/boot_id').read_text().strip(),cache/'cache')
    inner=StreamingController(create_demo_core('reuse'),jobs,output)
    owner=RecordingController(inner,transcriber=transcriber)
    report={'status':'RUNNING','actual_playback':True,'existing_services_modified':False,'cases':[]}
    try:
        for target,name in (('feedback','math_input.wav'),('answer','chat_input.wav')):
            check_idle()
            with wave.open(str(stage/'data'/name),'rb') as audio:pcm=audio.readframes(audio.getnframes())
            count=len(pcm)//2
            owner.utterance=CapturedAudio('cancel-'+uuid.uuid4().hex,AudioRef(1,0,count,FORMAT),pcm,0,round(count/16))
            owner.recording_state='READY';owner._queue_transcription()
            request_id=owner.transcription['request_id'];deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                check_idle();owner.tick();state=output.read()
                if inner.last_error or owner.transcription.get('error'):
                    raise RuntimeError(inner.last_error or owner.transcription['error'])
                if state.get('audible') and state.get('track')==target and state.get('clock',0)>.1:break
                time.sleep(.025)
            else:raise RuntimeError('Target playback phase not reached')
            started=time.monotonic();owner.cancel();settled=mouth_closed=None;frames=0
            while time.monotonic()-started<1.:
                frame=owner.tick();frames+=1;state=output.read()
                if inner.stream is not None or inner.turns:
                    raise RuntimeError('Cancelled stream remained active')
                gain=(frame or {}).get('speech_gain',0)
                if gain<=0 and mouth_closed is None:mouth_closed=time.monotonic()
                # Preserve the existing 180ms natural mouth-closing animation.
                # It must settle, and must never restart for late stream data.
                if gain>0 and time.monotonic()-started>.35:
                    raise RuntimeError('Cancelled mouth did not settle after its closing animation')
                if transcriber.last_ack and transcriber.last_ack['request_id']==request_id:
                    raise RuntimeError('Cancelled partial playback acknowledged history')
                if state.get('device_state')=='IDLE_READY' and settled is None:settled=time.monotonic()
                time.sleep(.025)
            if settled is None or mouth_closed is None:raise RuntimeError('Cancelled playback did not settle')
            deadline=time.monotonic()+10
            while get('http://192.168.50.1:8792/health')['busy']:
                if time.monotonic()>=deadline:raise RuntimeError('Host model ownership not released after cancel')
                time.sleep(.1)
            report['cases'].append({'cancelled_track':target,'request_id':request_id,'ready_after_cancel_ms':round((settled-started)*1000,2),
                                    'mouth_closed_after_cancel_ms':round((mouth_closed-started)*1000,2),
                                    'post_cancel_frames':frames,'history_ack_sent':False,'late_playback':False,
                                    'acoustic_tail_measured':False,'host_released':True})
        report['status']='PASS_REAL_FEEDBACK_AND_ANSWER_CANCEL'
    except Exception as exc:
        report.update(status='FAIL',error=type(exc).__name__+': '+str(exc));raise
    finally:
        owner.close();output.close();jobs.close()
        (stage/'cancellation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report))


if __name__=='__main__':main()
