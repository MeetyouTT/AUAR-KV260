"""Actual ASR/original LLM/TTS while synthetic face requests use separate CPU lock."""
import hashlib,http.client,json,runpy,statistics,sys,threading,time,urllib.request,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'aura'))
from common.face_features import PROTOCOL,MODEL_ID,encode_meta,checked_reply
from tests.framework.test_face_features import png
raw=png();stop=threading.Event();first=threading.Event();samples=[];errors=[];busy_rejections=[]
def features():
    fid=0
    while not stop.is_set():
        fid+=1;connection=None
        try:
            connection=http.client.HTTPConnection('192.168.50.1',8792,timeout=3)
            connection.request('GET','/health');health=json.loads(connection.getresponse().read());connection.close()
            m={'protocol':PROTOCOL,'model_id':MODEL_ID,'request_id':uuid.uuid4().hex,
                'target':{'camera_epoch':'synthetic-voice-coexistence','track_id':1,'track_generation':1},
                'frame_id':fid,'captured_mono_ms':int(time.monotonic()*1000),'sha256':hashlib.sha256(raw).hexdigest()}
            connection=http.client.HTTPConnection('192.168.50.1',8792,timeout=3);started=time.perf_counter()
            connection.request('POST','/v1/identity/face-features',body=raw,
                headers={'Content-Type':'image/png','X-Aura-Face':encode_meta(m)})
            response=connection.getresponse();data=json.loads(response.read(16385))
            if response.status==503:busy_rejections.append(fid)
            else:
                assert response.status==200;checked_reply(data,m)
                samples.append({'voice_busy':health['busy'],'roundtrip_ms':round((time.perf_counter()-started)*1000,3)})
                first.set()
        except Exception as exc:errors.append(type(exc).__name__+': '+str(exc)[:100])
        finally:
            if connection:connection.close()
        stop.wait(.3)
worker=threading.Thread(target=features,daemon=True);worker.start()
try:
    assert first.wait(6),'Feature probe did not start'
    runpy.run_path(str(HERE/'probe_voice_host.py'),run_name='__main__')
finally:
    stop.set();worker.join(5)
passed=bool(samples and sum(r['voice_busy'] for r in samples) and not errors)
report={'status':'PASS_REAL_ORIGINAL_VOICE_AND_CPU_FEATURE_COEXISTENCE' if passed else 'FAIL_COEXISTENCE',
    'face_input':'synthetic_112x112_png','success_count':len(samples),
    'while_voice_busy':sum(r['voice_busy'] for r in samples),'busy_rejections':len(busy_rejections),
    'median_ms':statistics.median(r['roundtrip_ms'] for r in samples) if samples else None,
    'max_ms':max((r['roundtrip_ms'] for r in samples),default=None),'errors':errors,
    'live_images_accessed':False,'user_database_opened':False,'actual_board_playback':False}
(HERE/'coexistence.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report));assert samples and report['while_voice_busy'] and not errors
