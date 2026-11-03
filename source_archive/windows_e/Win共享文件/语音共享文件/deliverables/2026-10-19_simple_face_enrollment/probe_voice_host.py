"""Historical audio, real ASR/TTS, bounded synthetic replies; no user enrollment."""
import hashlib,json,sys,threading,time,uuid,wave
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'aura'))
from board.runtime.audio.voice_channel import VoiceChannel
from common.voice_enrollment import result,render
with wave.open(str(ROOT/'deliverables/2026-10-18_stream_playback/chat_input.wav'),'rb') as audio:
    assert (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())==(16000,1,2)
    pcm=audio.readframes(audio.getnframes())
cases=[]
for mode in ('prepare','automatic','chat'):
    relay=mode!='chat'
    codes=('prepare_update_name',) if mode=='prepare' else ('sample_auto','registered')
    named=lambda code:'测试访客' if code=='prepare_update_name' else ''
    meta={'protocol':'aura-asr-1','board_boot_id':'simple-host-probe','session_id':uuid.uuid4().hex,
        'request_id':uuid.uuid4().hex,'generation':1,'capture_id':'historical-'+uuid.uuid4().hex,
        'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
    channel=VoiceChannel('192.168.50.1',8792,feedback=True);first=threading.Event();errors=[];end={};sender=None
    started=time.monotonic()
    def receive(header,payload):
        global sender,end
        if header['kind']=='transcript' and header.get('identity_request'):
            assert relay;token=header['identity_request']
            def guide():
                try:
                    for seq,code in enumerate(codes):
                        if seq and not first.wait(15):raise TimeoutError('Initial guidance PCM missing')
                        channel.identity_result(meta,token,result(code,named(code)),sequence=seq,final=seq==len(codes)-1)
                except BaseException as exc:errors.append(type(exc).__name__+': '+str(exc));channel.cancel()
            sender=threading.Thread(target=guide,daemon=True);sender.start()
        if header['kind']=='audio':first.set()
        if header['kind']=='end':end=header
    try:
        value=channel.exchange(meta,pcm,receive,enrollment_state=relay)
        if sender:sender.join(2)
        assert not errors,errors
    finally:channel.close()
    if relay:
        assert value['reply_text']==''.join(render(result(c,named(c))) for c in codes)
        assert end['timing']['llm']['backend']=='board_identity_workflow' and end['clauses']==len(codes)
    else:assert end['timing']['llm']['backend'] in ('ollama','llama_native_compact')
    cases.append({'mode':mode,'wall_seconds':round(time.monotonic()-started,3),'clauses':end['clauses'],
        'audio_seconds':value['sample_count']/24000,'tts_cache_hits':end.get('tts_cache_hits'),
        'first_pcm_ms':end.get('first_pcm_ms'),'backend':end['timing']['llm']['backend']})
report={'status':'PASS_REAL_ASR_TTS_UPFRONT_PROMPT_AUTOMATIC_RELAY_AND_ORIGINAL_CHAT',
    'historical_audio':True,'synthetic_board_replies_not_user_enrollment':True,'actual_board_playback':False,
    'identity_database_accessed':False,'camera_accessed':False,'cases':cases}
(HERE/'voice_host_probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report))
