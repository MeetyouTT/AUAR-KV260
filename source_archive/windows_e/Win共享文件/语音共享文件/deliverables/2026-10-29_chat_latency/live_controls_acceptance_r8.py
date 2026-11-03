"""Actual ASR/TTS memory round trip using public synthetic input; no mic/playback."""
import hashlib,json,subprocess,sys,time,uuid,wave
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A))
from board.runtime.audio.voice_channel import VoiceChannel
from common.memory_commands import parse_command
from common.memory_controls import parse
assert json.loads((H/'deployment_r8.json').read_text(encoding='utf-8'))['status']=='COMMITTED'
assert not (H/'live_controls_acceptance.json').exists(),'Inspect existing test receipt before repeating'
report={'status':'RUNNING','started_unix':time.time(),'conversation_id':uuid.uuid4().hex,
        'session_id':uuid.uuid4().hex,'turns':[],'scope':'public synthetic anonymous session; no mic/playback/ACK'}
def save():(H/'live_controls_acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def ps(args,timeout=25):
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',*args],capture_output=True,timeout=timeout)
    assert not result.returncode,(result.stdout+result.stderr).decode(errors='replace')[-400:]
def cleanup():
    python=r'C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    command='"'+python+'" -B "'+str(H/'cleanup_public_probe.py')+'"'
    launch="$s=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0};"+"$p=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='"+command+"';ProcessStartupInformation=$s};if($p.ReturnValue -ne 0){throw 'Public cleanup launch failed'}"
    ps(['-Command',launch]);until=time.monotonic()+20
    while time.monotonic()<until and not (H/'public_probe_cleanup.json').exists():time.sleep(.2)
    value=json.loads((H/'public_probe_cleanup.json').read_text(encoding='utf-8'));assert value['status']=='PASS',value
    report['cleanup']=value
questions=[
 ('set','记住，颜色是蓝色'),('correct','更正记忆，颜色是绿色'),
 ('history','查看颜色记忆历史'),('previous','我以前喜欢什么颜色'),('preview','删除刚才关于蓝色的对话记录'),
 ('confirm','确认删除这些对话记录'),('history_after','查看颜色记忆历史'),
 ('indexed_history','查看颜色第一条记忆历史'),('current_question','我喜欢什么颜色'),
 ('forget','忘记颜色的记忆'),('unknown_question','我喜欢什么颜色'),
 ('plain_today','我今天有点累，陪我聊聊'),
 ('recall_today','今天我们聊了什么'),
 ('general_durable_question','请简短介绍一下你自己')]
try:
    for index,(label,text) in enumerate(questions,1):
        audio=H/('public_'+label+'.wav')
        ps(['-File',str(H/'synthesize_question.ps1'),'-Text',text,'-OutputPath',str(audio)])
        with wave.open(str(audio),'rb') as source:
            assert (source.getframerate(),source.getnchannels(),source.getsampwidth())==(16000,1,2)
            pcm=source.readframes(source.getnframes())
        context={'protocol':'aura-asr-1','board_boot_id':'public-memory-controls-test','session_id':report['session_id'],
          'request_id':uuid.uuid4().hex,'generation':index,'capture_id':'public-synthetic-'+label,
          'sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
        row={'label':label,'public_input':text,'context':context};report['turns'].append(row);save()
        started=time.monotonic();first_audio=None;transcript='';end={};digest=hashlib.sha256()
        def receive(header,payload):
            global first_audio,transcript
            if header['kind']=='transcript':transcript=header['text']
            if header['kind']=='audio':
                digest.update(payload)
                if first_audio is None:first_audio=round((time.monotonic()-started)*1000,2)
            if header['kind']=='end':end.update(header)
        channel=VoiceChannel('192.168.50.1')
        try:result=channel.exchange(context,pcm,receive,conversation=report['conversation_id'])
        finally:channel.close()
        assert result['network_complete'] and result['sample_count']>0 and result['pcm_sha256']==digest.hexdigest()
        assert not result['playback_verified']
        reply=result['reply_text'];row.update(transcript=transcript,reply=reply,first_pcm_ms=first_audio,
            sample_count=result['sample_count'],pcm_sha256=result['pcm_sha256'],timing=end.get('timing',{}),playback_ack_sent=False)
        save()
        if label in ('set','correct'):
            command=parse_command(transcript);assert command and command['operation']=='set' and command['value']==('蓝色' if label=='set' else '绿色'),transcript
        elif label in ('history','history_after','previous'):
            assert parse(transcript)['op']=='history',transcript
            assert '绿色' in reply and (('蓝色' in reply) if label in ('history','previous') else ('蓝色' not in reply)),reply
        elif label=='indexed_history':
            command=parse(transcript);assert command and command.get('index')==1 and '绿色' in reply and '蓝色' not in reply,(transcript,reply)
        elif label=='preview':
            command=parse(transcript);assert command and command['op']=='preview' and command['topic']=='蓝色',transcript
            assert '找到' in reply and '确认删除这些对话记录' in reply,reply
        elif label=='confirm':
            assert parse(transcript)['op']=='confirm' and '已删除' in reply,reply
        elif label=='current_question':
            assert '绿色' in reply and '蓝色' not in reply and row['timing']['llm']['backend']=='conversation_memory_command',reply
        elif label=='forget':assert parse_command(transcript)['operation']=='forget' and '移除' in reply,reply
        elif label=='unknown_question':
            assert '没有明确记住' in reply and '绿色' not in reply and '蓝色' not in reply and row['timing']['llm']['backend']=='conversation_memory_command',reply
        elif label=='plain_today':
            assert row['timing']['llm']['backend']=='ollama'
            # This foreign public boot has no live visual cache. Its durable
            # conversation messages remain, without an added archive summary.
            assert row['timing']['history_messages']==row['timing']['conversation_context']['history_messages'],row['timing']
        elif label=='recall_today':
            assert row['timing']['llm']['backend']=='ollama' and row['timing']['history_messages']>=1,row['timing']
        else:assert len(reply)>3 and row['timing']['llm']['backend']=='ollama',reply
        row['status']='PASS';save()
        print(json.dumps({'label':label,'status':'PASS','first_pcm_ms':first_audio,'samples':result['sample_count']},ensure_ascii=True),flush=True)
    report['status']='PASS'
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
finally:
    save()
    try:cleanup()
    except Exception as exc:report.update(status='FAIL',cleanup_error=type(exc).__name__+': '+str(exc))
    report['finished_unix']=time.time();save()
print(json.dumps({'status':report['status'],'checks':len([r for r in report['turns'] if r.get('status')=='PASS']),'cleanup':report.get('cleanup')},ensure_ascii=True))
raise SystemExit(0 if report['status']=='PASS' else 1)

