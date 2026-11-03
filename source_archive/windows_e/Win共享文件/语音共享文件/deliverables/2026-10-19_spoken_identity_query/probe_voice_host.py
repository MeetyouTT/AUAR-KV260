"""Real historical audio/ASR/TTS query relay, synthetic board decision, no live face."""
import hashlib,json,sys,time,uuid,wave
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'aura'))
from board.runtime.audio.voice_channel import VoiceChannel
from common.voice_enrollment import result,render
with wave.open(str(ROOT/'deliverables/2026-10-18_stream_playback/chat_input.wav'),'rb') as audio:
    assert (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())==(16000,1,2)
    pcm=audio.readframes(audio.getnframes())
cases=[]
for code in ('identity_seen','identity_unknown','identity_unavailable'):
    meta={'protocol':'aura-asr-1','board_boot_id':'public-query-host-probe','session_id':uuid.uuid4().hex,
        'request_id':uuid.uuid4().hex,'generation':1,'capture_id':'historical-'+uuid.uuid4().hex,
        'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
    channel=VoiceChannel('192.168.50.1',8792,feedback=True,identity_query=True);end={};seen=[]
    value=result(code,'测试访客' if code=='identity_seen' else '')
    def receive(header,payload):
        if header['kind']=='transcript':
            assert header.get('identity_request');seen.append(True)
            channel.identity_result(meta,header['identity_request'],value)
        if header['kind']=='end':end.update(header)
    started=time.monotonic()
    try:reply=channel.exchange(meta,pcm,receive,enrollment_state=True)
    finally:channel.close()
    assert seen and reply['reply_text']==render(value)
    assert end['timing']['llm']['backend']=='board_identity_workflow'
    assert end['timing']['llm']['identity_reply_code']==code and end['clauses']==1
    cases.append({'code':code,'wall_seconds':round(time.monotonic()-started,3),
        'first_pcm_ms':end.get('first_pcm_ms'),'audio_seconds':reply['sample_count']/24000,
        'clauses':end['clauses'],'tts_cache_hits':end.get('tts_cache_hits')})
report={'status':'PASS_REAL_ASR_ORIGINAL_TTS_BOARD_QUERY_REPLIES',
    'historical_audio':True,'synthetic_board_query_reply':True,'actual_query_intent_asr_audio':False,
    'actual_board_playback':False,'user_identity_database_accessed':False,'live_images_accessed':False,
    'cases':cases,'scope':'HTTP query intent routing is covered by controlled-transcript tests; this probe checks real ASR/TTS relay.'}
(HERE/'voice_host_probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
