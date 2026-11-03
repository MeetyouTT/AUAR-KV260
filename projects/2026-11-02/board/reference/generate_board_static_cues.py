"""Generate public role cues through the fixed host, store only on the board."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(PROJECT/'deliverables/2026-10-18_board_dialogue')]
from board_ssh import ssh
from resume_baseline import write_json

SCRIPT=r'''
import hashlib,io,json,os,signal,time,urllib.request,uuid,wave
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
code=Path(CODE)
sys.path.insert(0,str(code))
from board.runtime.board_dialogue_client import InferenceHttpClient
from common.model_inference_wire import decode_audio
from common.voice_wire import PROTOCOL,REVISION,wav_payload
from tools.board_business_gui import local_feedback_provider
signal.alarm(80)
with urllib.request.urlopen('http://192.168.50.1:8797/health',timeout=2) as response:health=json.load(response)
assert health['protocol_version']==1 and health['role']=='model_inference_only' and health['ok'] is True
assert health['backend']['tts']=='omnivoice' and health['backend']['num_step']==16 and health['backend']['tts_ready'] is True
parent=Path('/home/root/aura-board-owner-candidate-20261030')
target=parent/('xuefei-static-cues-'+uuid.uuid4().hex[:16]);target.mkdir(mode=0o700)
texts={'thinking':('让我想一想。','neutral'),
       'arrival':('你好，我是雪妃，很高兴认识你。','friendly'),
       'invitation':('想聊聊时，可以叫我雪妃。','friendly')}
client=InferenceHttpClient('192.168.50.1',8797)
assets={};rows=[]
for generation,(name,(text,emotion)) in enumerate(texts.items(),1):
 body=dict(protocol_version=1,request_id=uuid.uuid4().hex,board_boot_id=BOOT,
           session_id=target.name,generation=generation,budget_ms=20000,text=text)
 at=time.monotonic();result=client.request('tts',body,deadline=at+20)
 assert result['ok'] is True
 pcm,rate=decode_audio(result['result']['audio']);assert rate==24000 and len(pcm)>0
 stream=io.BytesIO()
 with wave.open(stream,'wb') as out:
  out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate);out.writeframes(pcm)
 raw=stream.getvalue();duration=len(pcm)/2/rate;assert 0<duration<=5
 meta=dict(protocol=PROTOCOL,source_kind='actual',engine='omnivoice',revision=REVISION,
           num_step=16,reply_text=text,emotion=emotion,sha256=hashlib.sha256(raw).hexdigest(),
           bytes=len(raw),duration_seconds=duration)
 wav_payload(meta,raw)
 path=target/(name+'.wav')
 fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
 assets[name]=dict(path=str(path),metadata=meta)
 rows.append(dict(name=name,path=str(path),text=text,sha256=meta['sha256'],samples=len(pcm)//2,
                  duration_seconds=duration,model_seconds=round(time.monotonic()-at,3)))
manifest=target/'feedback.json';raw=json.dumps(dict(version=1,assets=assets),ensure_ascii=False,sort_keys=True,indent=2).encode()
fd=os.open(str(manifest),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
assert set(local_feedback_provider(manifest)())==set(assets)
signal.alarm(0)
print(json.dumps(dict(status='ACTUAL_FIXED_VOICE_PUBLIC_STATIC_CUES_STORED_ON_BOARD',
 manifest=str(manifest),manifest_sha256=hashlib.sha256(raw).hexdigest(),assets=rows,
 profile_version='xuefei-yuki-board-v1-candidate',voice_engine_contract=PROTOCOL,
 voice_engine_revision=REVISION,num_step=16,model_host='192.168.50.1:8797',
 actual_microphone_opened=False,actual_audio_played=False,existing_database_accessed=False,
 original_asset_overwritten=False,windows_audio_archive_created=False,
 purpose='Public fixed interface cues, not user dialogue memory',provenance='Original fixed model-only host and accepted voice_wire conversion')))
'''


def main():
    gate=json.loads((HERE.parent/'coordination/runtime_windows.json').read_text(encoding='utf-8-sig'))
    if gate['performance_window'].get('state')!='BUSINESS_ACCEPTANCE_EXCLUSIVE':raise RuntimeError('Root window required')
    stage=json.loads((HERE/'resume_bundle/staged.json').read_text(encoding='utf-8'))
    prefix='import sys\nBOOT='+repr(gate['performance_window']['board_boot'])+'\nCODE='+repr(stage['candidate_root']+'/code')+'\n'
    now=datetime.datetime.now(datetime.timezone.utc)
    value=json.loads(ssh('python3 -B -',prefix+SCRIPT,timeout=90))
    output=HERE/'resume_runtime/actual_static_cues.json'
    write_json(output,dict(checked_utc=now.isoformat(),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),**value))
    print(json.dumps(dict(output=str(output),**value),ensure_ascii=True))


if __name__=='__main__':main()
