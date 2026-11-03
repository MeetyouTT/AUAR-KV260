"""ASR wording check of the four real locally generated clips."""
import json
from pathlib import Path
import re
import sys
import wave
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent.parent/'aura'))
from board.runtime.audio.asr import SherpaOfflineRecognizer,AsrConfig
recognizer=SherpaOfflineRecognizer(AsrConfig(prefer_int8=True));rows=[]
for row in json.loads((HERE/'voice_manifest.json').read_text(encoding='utf-8'))['clips']:
    path=HERE/'cache'/f"{row['key']}.wav"
    with wave.open(str(path),'rb') as stream:samples=np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2').astype(np.float32)/32768
    actual=recognizer.transcribe(samples,24000);expected=row['identity']['text'];normalize=lambda s:re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]','',s)
    rows.append({'id':row['id'],'text':expected,'asr_text':actual,'exact_without_punctuation':normalize(actual)==normalize(expected),
                 'note':'Character-name homophones need human listening; ASR is not voice-tone acceptance.'})
result={'model':recognizer.stats(),'rows':rows};(HERE/'asr_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(rows,ensure_ascii=False))
