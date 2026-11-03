"""Check new audio, accepted-track integrity, blink metadata and local routes."""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
import urllib.error
import wave
import numpy as np

HERE=Path(__file__).resolve().parent;AURA=HERE.parent.parent/'aura';sys.path.insert(0,str(AURA))
from board.runtime.audio.selected_voice import SelectedVoiceSynthesizer

def main():
    synth=SelectedVoiceSynthesizer(HERE/'cache');clips=[]
    for file in (HERE/'cache').glob('*.json'):
        record=json.loads(file.read_text(encoding='utf-8'));cached=synth.cached(record['identity']['text'])
        assert cached and cached['sha256']==record['sha256'] and cached['cache_hit']
        with wave.open(cached['path'],'rb') as stream:pcm=np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2')
        assert len(pcm) and np.max(np.abs(pcm.astype(float)))>1000
        assert not np.any(np.abs(pcm.astype(float))>=32767)
        clips.append({k:record[k] for k in ('key','sha256','identity','duration_seconds','generation_seconds')})
    assert clips
    previous=HERE.parent/'2026-10-06_voice_script_sync/audio/script.wav'
    same_track=hashlib.sha256(previous.read_bytes()).hexdigest()==hashlib.sha256((HERE/'audio/script.wav').read_bytes()).hexdigest()
    assert same_track
    timeline=json.loads((HERE/'timeline.json').read_text(encoding='utf-8'))
    blink_rows=[r for r in timeline['samples'] if r['blink_active']]
    speaking=[r for r in blink_rows if r['speech_gain']>.1];assert speaking
    checks=[]
    for path,headers,expected in [('audio/script.wav',{'Range':'bytes=0-43'},206),
                                 ('audio/script.wav',{'Range':'bytes=-10'},206),
                                 ('live_assets.json',{},200),
                                 ('cache/'+clips[0]['key']+'.wav',{'Range':'bytes=24-63'},206),
                                 ('%2e%2e/acceptance.json',{},404),('worker.log',{},404),
                                 ('audio/script.wav',{'Range':'bytes=999999999-'},416)]:
        request=urllib.request.Request('http://127.0.0.1:8772/'+path,headers=headers)
        try:
            with urllib.request.urlopen(request,timeout=5) as response:code=response.status;size=len(response.read())
        except urllib.error.HTTPError as exc:code=exc.code;size=None
        assert code==expected,(path,code,expected)
        if headers.get('Range')=='bytes=0-43':assert size==44
        checks.append({'path':path,'status':code,'bytes':size})
    result={'status':'PASS','new_clips':clips,'repeat_cache_verified':True,'accepted_script_audio_unchanged':same_track,
            'blink_cached_samples':len(blink_rows),'blink_while_speaking_samples':len(speaking),'http_checks':checks,
            'voice_reference_sha256':synth.selection['reference_sha256'],'mouth_scope':'amplitude, not phoneme alignment'}
    (HERE/'delivery_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
