"""Synthetic speaker tests and fixed public speech; never accesses personal store."""
import io,json,os,socket,sys,tempfile,time,unittest,wave
from pathlib import Path
HERE=Path(__file__).resolve().parent
temporary=HERE/'speaker_tmp'
temporary.mkdir(exist_ok=True)
tempfile.tempdir=str(temporary)
sys.path.insert(0,str(HERE.parents[1]/'aura'))
os.environ['AURA_PUBLIC_SPEAKER_SAMPLES']='D:/AIModels/speaker-identity/public-samples'
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
def blocked(*a,**kw):raise RuntimeError('Network disabled for public speaker tests')
socket.socket.connect=blocked;socket.socket.connect_ex=blocked
out=io.StringIO();suite=unittest.TestSuite()
for module in ('tests.framework.test_speaker_identity','tests.framework.test_speaker_vad_live'):
    suite.addTests(unittest.defaultTestLoader.loadTestsFromName(module))
result=unittest.TextTestRunner(stream=out,verbosity=2).run(suite)
value={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,
       'skipped':len(result.skipped),'test_log':out.getvalue(),'network_disabled':True,
       'personal_database_accessed':False,'production_integrated_by_this_test':False}
if result.wasSuccessful():
    import torch
    torch.set_num_threads(2)
    from common.speaker_identity import EcapaEncoder
    encoder=EcapaEncoder('D:/AIModels/speaker-identity/ecapa')
    vectors={};times=[]
    for person in (1,2):
        for sentence in (1,2):
            name=f'spk{person}_snt{sentence}'
            with wave.open('D:/AIModels/speaker-identity/public-samples/'+name+'.wav','rb') as f:
                assert (f.getframerate(),f.getnchannels(),f.getsampwidth())==(16000,1,2)
                pcm=f.readframes(f.getnframes())
            start=time.perf_counter();vectors[name]=encoder.encode(pcm);times.append((time.perf_counter()-start)*1000)
    value['public_model']={'model_id':encoder.model_id,'inference_ms':times,
        'same_speaker_cosine':[sum(a*b for a,b in zip(vectors[f'spk{p}_snt1'],vectors[f'spk{p}_snt2'])) for p in (1,2)],
        'different_speaker_cosine':sum(a*b for a,b in zip(vectors['spk1_snt1'],vectors['spk2_snt2'])),
        'field_threshold_selected':False,'field_accuracy_validated':False}
(HERE/'speaker_auto_tests.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(value))
raise SystemExit(0 if value['status']=='PASS' else 1)
