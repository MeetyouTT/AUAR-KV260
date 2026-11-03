"""Actual ASR/OmniVoice phase relay and ordinary 27B; no board playback or DB."""
import hashlib,json,sys,threading,time,uuid,wave
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from board.runtime.audio.voice_channel import VoiceChannel
from common.voice_enrollment import result,render
with wave.open(str(ROOT/'deliverables/2026-10-18_stream_playback/chat_input.wav'),'rb') as audio:
    assert (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())==(16000,1,2)
    pcm=audio.readframes(audio.getnframes())
cases=[]
for relay in (True,False):
    meta={'protocol':'aura-asr-1','board_boot_id':'sampling-host-probe','session_id':uuid.uuid4().hex,
        'request_id':uuid.uuid4().hex,'generation':1,'capture_id':'historical-'+uuid.uuid4().hex,
        'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
    channel=VoiceChannel('192.168.50.1',8792,feedback=True);events=[];started=time.monotonic();end={}
    first_audio=threading.Event();errors=[];sender=None
    codes=('sample_front','sample_validate','confirm_update_name')
    def receive(header,payload):
        global end,sender
        events.append(header['kind'])
        if header['kind']=='transcript' and header.get('identity_request'):
            assert relay;token=header['identity_request']
            def guide():
                try:
                    for seq,code in enumerate(codes):
                        if seq==1 and not first_audio.wait(15):raise TimeoutError('No first sampling prompt PCM')
                        channel.identity_result(meta,token,result(code,'测试访客' if code=='confirm_update_name' else ''),sequence=seq,final=seq==2)
                        if seq<2:time.sleep(.2)
                except BaseException as exc:errors.append(type(exc).__name__+': '+str(exc));channel.cancel()
            sender=threading.Thread(target=guide,daemon=True);sender.start()
        if header['kind']=='audio':first_audio.set()
        if header['kind']=='end':end=header
    try:
        value=channel.exchange(meta,pcm,receive,enrollment_state=relay)
        if sender:sender.join(2)
        assert not errors,errors
    finally:channel.close()
    if relay:
        assert value['reply_text']==''.join(render(result(c,'测试访客' if c=='confirm_update_name' else '')) for c in codes)
        assert end['timing']['llm']['backend']=='board_identity_workflow' and end['clauses']==3
    else:assert end['timing']['llm']['backend'] in ('ollama','llama_native_compact')
    cases.append({'mode':'controlled_natural_enrollment_identity_relay' if relay else 'ordinary_chat',
        'seconds':round(time.monotonic()-started,3),'samples':value['sample_count'],'audio_seconds':round(value['sample_count']/24000,3),
        'timing':end['timing'],'clauses':end['clauses'],'events':sorted(set(events)),
        'tts_cache_hits':end.get('tts_cache_hits'),'first_pcm_ms':end.get('first_pcm_ms')})
report={'status':'PASS_REAL_NATURAL_ENROLLMENT_ASR_TTS_RELAY_AND_ORIGINAL_27B_CHAT','historical_audio':True,
    'synthetic_guidance_not_user_registration':True,'actual_board_playback':False,'identity_database_accessed':False,
    'sampling_camera_accessed':False,'cases':cases}
(HERE/'voice_host_probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
