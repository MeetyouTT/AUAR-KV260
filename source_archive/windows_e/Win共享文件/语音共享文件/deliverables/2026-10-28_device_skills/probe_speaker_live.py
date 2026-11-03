"""Public reference recording through the real CPU enrollment service, then cancel."""
import base64,hashlib,json,sqlite3,time,urllib.request,uuid,wave
from pathlib import Path
H=Path(__file__).resolve().parent
sample=Path(r'D:\AIModels\speaker-identity\public-samples\spk1_snt2.wav')
assert hashlib.sha256(sample.read_bytes()).hexdigest()=='e1f125a318f4026991bf78f5c41481be0fbcf9b3b2fd72284f9824cb851c3034'
with wave.open(str(sample)) as f:
 assert (f.getnchannels(),f.getframerate(),f.getsampwidth())==(1,16000,2)
 pcm=f.readframes(f.getnframes())
session=uuid.uuid4().hex
def meta(n):return {'protocol':'aura-asr-1','board_boot_id':'public-sample-automatic-test','session_id':session,
 'request_id':session+'-'+str(n),'generation':n,'capture_id':'speechbrain-spk1-snt2','sample_count':len(pcm)//2,
 'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':20000}
def post(path,v):
 r=urllib.request.Request('http://127.0.0.1:8812'+path,data=json.dumps(v).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(r,timeout=15) as f:return json.load(f)
def turn(n,text):return post('/v1/speaker/turn',{'context':meta(n),'text':text,'pcm':base64.b64encode(pcm).decode()})['reply']
def counts():
 p=Path.home()/'AppData/Local/Aura/device-memory/speakers.sqlite3'
 with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
  return {'identities':db.execute('SELECT COUNT(*) FROM identities').fetchone()[0],
          'revision':db.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]}
before=counts();report={'sample_sha256':hashlib.sha256(sample.read_bytes()).hexdigest(),'sample_seconds':len(pcm)/32000,
 'scope':'public PCM; explicit synthetic ASR text; real VAD and ECAPA service; cancellation before save','before':before}
try:
 assert '开始登记' in turn(1,'登记我的声纹，我叫自动测试')
 t=time.monotonic();reply=turn(2,'这是一段公开参考录音。');report['sample_seconds_inference']=round(time.monotonic()-t,3)
 report['sample_reply']=reply
 assert '收到' in reply,reply
 assert '已经用过' in turn(3,'这是一段公开参考录音。')
 assert counts()==before
finally:
 report['cancel_reply']=turn(4,'取消声纹登记')
report['state']=post('/v1/speaker/state',{'context':meta(5)})
assert not report['state']['active'] and not report['state']['automatic_profile_access']
report['after']=counts();assert report['after']==before
report.update(status='PASS',raw_audio_saved=False,personal_identity_created=False,field_accuracy_validated=False)
(H/'speaker_live_acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
