"""Wait for original service and verify real reply, source, model, and board."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

BASE=Path(__file__).resolve().parent
HERE=Path(os.environ.get('AURA_TTS_TRIAL_DIR',str(BASE)))
ROOT=BASE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

def get(url):
    with urllib.request.urlopen(url,timeout=5) as response:return json.load(response)

def main():
    deadline=time.monotonic()+420
    while True:
        try:
            health=get('http://192.168.50.1:8792/health')
            if health.get('ready') and not health.get('busy'):break
        except (OSError,ValueError):pass
        if time.monotonic()>deadline:raise TimeoutError('Original service did not become ready')
        time.sleep(2)
    assert health['llm_model']=='aura-qwen3.8-27b-abliterated:iq4_xs' and health['tts']=='omnivoice' and health['num_step']==16
    print(json.dumps({'stage':'original_service_ready'}),flush=True)
    assert all(health['latency_options'].get(name) for name in ('reply_first','early_sentence','coalesce_chat','reuse_history','compact_grammar'))
    before=json.loads((BASE/'before.json').read_text(encoding='utf-8'))
    source={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value for name,value in before['source_hashes'].items()}
    assert all(source.values()),source
    print(json.dumps({'stage':'source_unchanged','files':len(source),'next':'27B_SHA256'}),flush=True)
    target=Path('D:/AIModels/Ollama-AURA/blobs/sha256-d83adbbbaace8acdfcfe28004f779326176b9df00b4ec99dc6c24d749723d3b9')
    reuse=HERE/'model_hash_reuse.json'
    if reuse.is_file():
        checkpoint=json.loads(reuse.read_text(encoding='utf-8'))
        previous=json.loads(Path(checkpoint['prior_report']).read_text(encoding='utf-8'))
        stat=target.stat()
        assert previous['status']=='PASS_ORIGINAL_RESTORED_ACTUAL_CHANNEL' and previous['model_sha256']==checkpoint['sha256']
        assert [stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns,stat.st_ino]==[checkpoint['size'],checkpoint['mtime_ns'],checkpoint['ctime_ns'],checkpoint['file_id']]
        actual_hash=checkpoint['sha256'];hash_method='immediate_prior_full_SHA256_plus_unchanged_file_identity_and_timestamps'
    else:
        digest=hashlib.sha256()
        with target.open('rb') as f:
            for block in iter(lambda:f.read(8*1024*1024),b''):digest.update(block)
        actual_hash=digest.hexdigest();hash_method='full_SHA256'
    assert actual_hash=='d83adbbbaace8acdfcfe28004f779326176b9df00b4ec99dc6c24d749723d3b9'
    print(json.dumps({'stage':'27B_hash_verified','next':'board_health_and_real_voice_channel'}),flush=True)
    board=json.loads(ssh('python3 -','import json,pathlib,urllib.request\ncamera=json.load(urllib.request.urlopen("http://127.0.0.1:8790/health",timeout=4))\nprint(json.dumps({"boot_id":pathlib.Path("/proc/sys/kernel/random/boot_id").read_text().strip(),"camera":camera}))'))
    assert not board['camera'].get('camera_error') and not board['camera'].get('detector_error')
    from tools.probe_voice_channel import probe
    actual=probe('192.168.50.1',8792,ROOT/'aura/report/recording_20261016/microphone-5s.wav',rounds=1,output=HERE/'restored.wav')
    value={'status':'PASS_ORIGINAL_RESTORED_ACTUAL_CHANNEL','health':health,'asr':get('http://192.168.50.1:8791/health'),'protected_source_checks':source,'model_sha256':actual_hash,'model_hash_method':hash_method,'board':board,'channel':actual,'physical_playback_tested':False}
    (HERE/'restored.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':value['status'],'source_files':len(source),'first_pcm_ms':actual['turns'][0]['first_pcm_ms'],'camera_pid':board['camera']['pid']},ensure_ascii=True))

if __name__=='__main__':main()
