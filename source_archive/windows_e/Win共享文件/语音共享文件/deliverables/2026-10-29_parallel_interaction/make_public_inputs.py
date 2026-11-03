"""Public synthetic ASR inputs only; selected doll reply voice is untouched."""
import hashlib,json,subprocess,wave
from pathlib import Path
H=Path(__file__).resolve().parent
spec=[('short','今天我想练习说一句话，请鼓励我，顺便提醒我慢慢来。'),
 ('medium','请用两句话介绍雨后散步的乐趣，别重复我的问题。'),
 ('long','请讲一段大约八十字的小故事，主角是一只在雨后找到彩虹的小猫。')]
rows=[]
for label,text in spec:
    target=H/('public_gpu_'+label+'.wav')
    if not target.exists():
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
          str(H.parent/'2026-10-29_chat_latency/synthesize_question.ps1'),'-Text',text,'-OutputPath',str(target)],
          capture_output=True,check=True,timeout=20)
    with wave.open(str(target),'rb') as f:
        assert (f.getframerate(),f.getnchannels(),f.getsampwidth())==(16000,1,2)
        assert 3200<=f.getnframes()<=320000
        rows.append(dict(label=label,text=text,file=target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),samples=f.getnframes()))
(H/'public_inputs.json').write_text(json.dumps(dict(status='PASS',purpose='public synthetic ASR calibration input',
 microphone_opened=False,physical_playback=False,production_reply_voice_changed=False,inputs=rows),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','public_wavs':len(rows),'microphone_opened':False,'physical_playback':False}))
