"""Independent recognition of the locally synthesized demonstration sentence."""
import json
from pathlib import Path
import re
import sys
import wave
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent.parent/'aura'))
from board.runtime.audio.asr import SherpaOfflineRecognizer,AsrConfig
recognizer=SherpaOfflineRecognizer(AsrConfig(prefer_int8=True))
rows=[]
for file in (HERE/'cache').glob('*.json'):
    data=json.loads(file.read_text(encoding='utf-8'))
    with wave.open(str(file.with_suffix('.wav')),'rb') as audio:
        samples=np.frombuffer(audio.readframes(audio.getnframes()),dtype='<i2').astype(np.float32)/32768
    actual=recognizer.transcribe(samples,24000);expected=data['identity']['text']
    normalized=lambda s:re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]','',s)
    rows.append({'text':expected,'asr_text':actual,'exact_without_punctuation':normalized(actual)==normalized(expected),
                 'note':'ASR checks words; it is not a human voice-tone judgement'})
(HERE/'asr_verification.json').write_text(json.dumps({'rows':rows,'model':recognizer.stats()},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False))
