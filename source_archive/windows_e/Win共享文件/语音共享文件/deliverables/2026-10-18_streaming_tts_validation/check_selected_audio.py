"""Validate only the selected 25-token configuration, keeping other modes distinct."""
import json
import os
from pathlib import Path
from probe_cuda_variants import transcribe,normalize,distance

BASE=Path(__file__).resolve().parent
HERE=Path(os.environ['AURA_TTS_TRIAL_DIR'])
source=BASE/'cuda-cli-validated/f16_no_flash/streaming.json'
data=json.loads(source.read_text(encoding='utf-8'))
checks=[]
for item in data['cases']:
    if item['chunk_tokens']!=25:continue
    text=transcribe(item['wav'])
    checks.append({'wav':item['wav'],'expected':item['text'],'asr_text':text,'pcm_sha256':item['pcm_sha256'],'character_error_rate':distance(normalize(item['text']),normalize(text))/len(normalize(item['text']))})
assert len(checks)==4
value={'status':'SELECTED_MODE_CONTENT_SCREEN','selected_chunk_tokens':25,'cases':checks,'voice_similarity':'PENDING_LISTENING'}
(HERE/'audio_content.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
