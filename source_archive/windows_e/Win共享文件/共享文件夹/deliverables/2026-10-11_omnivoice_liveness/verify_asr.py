"""Independent CPU transcription probe, not a naturalness score."""
import importlib.metadata as metadata
import json
from pathlib import Path
import re
import sys
import wave

import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'aura'))
from board.runtime.audio.asr import SherpaOfflineRecognizer,AsrConfig


def normalized(value):
    return re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]','',value).lower()


def distance(a,b):
    previous=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        row=[i]
        for j,y in enumerate(b,1):
            row.append(min(row[-1]+1,previous[j]+1,previous[j-1]+(x!=y)))
        previous=row
    return previous[-1]


def main():
    recognizer=SherpaOfflineRecognizer(AsrConfig(prefer_int8=True))
    rows=[]
    for path in sorted((HERE/'runs').glob('*/report.json')):
        report=json.loads(path.read_text(encoding='utf-8'))
        for clip in report['clips']:
            with wave.open(str(HERE/clip['file'])) as audio:
                rate=audio.getframerate()
                if audio.getsampwidth()!=2 or audio.getnchannels()!=1:
                    raise ValueError('Unsupported WAV')
                samples=np.frombuffer(audio.readframes(audio.getnframes()),dtype='<i2').astype(np.float32)/32768
            actual=recognizer.transcribe(samples,rate)
            expected=clip['text']
            error=distance(normalized(expected),normalized(actual))
            row=dict(engine=path.parent.name,id=clip['id'],text=expected,asr_text=actual,
                     edit_distance=error,cer=error/max(1,len(normalized(expected))),
                     exact_without_punctuation=normalized(expected)==normalized(actual))
            rows.append(row)
            print(path.parent.name+'/'+clip['id']+': '+actual,flush=True)
    result=dict(rows=rows,model=recognizer.stats(),sherpa_version=metadata.version('sherpa-onnx'),
                note='ASR may misrecognize names/homophones; this is not a human voice-tone or pronunciation judgement.')
    (HERE/'asr_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ASR checked',len(rows),'clips; exact text',sum(r['exact_without_punctuation'] for r in rows),flush=True)


if __name__=='__main__':
    main()
