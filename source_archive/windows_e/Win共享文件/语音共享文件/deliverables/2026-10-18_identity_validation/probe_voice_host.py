"""Historical ASR + actual OmniVoice relay and normal 27B; no board playback/DB."""
import hashlib,json,sys,time,uuid,wave
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
    meta={'protocol':'aura-asr-1','board_boot_id':'identity-host-probe','session_id':uuid.uuid4().hex,
        'request_id':uuid.uuid4().hex,'generation':1,'capture_id':'historical-'+uuid.uuid4().hex,
        'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
    channel=VoiceChannel('192.168.50.1',8792,feedback=True);events=[];started=time.monotonic();end={}
    def receive(header,payload):
        global end
        events.append(header['kind'])
        if header['kind']=='transcript' and header.get('identity_request'):
            assert relay
            channel.identity_result(meta,header['identity_request'],result('cancelled'))
        if header['kind']=='end':end=header
    try:
        value=channel.exchange(meta,pcm,receive,enrollment_state=relay)
    finally:channel.close()
    if relay:assert value['reply_text']==render(result('cancelled')) and end['timing']['llm']['backend']=='board_identity_workflow'
    else:assert end['timing']['llm']['backend'] in ('ollama','llama_native_compact')
    cases.append({'mode':'controlled_identity_relay' if relay else 'ordinary_chat','reply_text':value['reply_text'],
        'seconds':round(time.monotonic()-started,3),'timing':end['timing'],'samples':value['sample_count'],
        'pcm_sha256':value['pcm_sha256'],'events':sorted(set(events)),'tts_cache_hits':end.get('tts_cache_hits'),
        'first_pcm_ms':end.get('first_pcm_ms')})
report={'status':'PASS_REAL_ASR_TTS_RELAY_AND_27B_CHAT','historical_audio':True,'actual_board_playback':False,
    'identity_database_accessed':False,'controlled_reply_not_user_registration':True,'cases':cases}
(HERE/'voice_host_probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
