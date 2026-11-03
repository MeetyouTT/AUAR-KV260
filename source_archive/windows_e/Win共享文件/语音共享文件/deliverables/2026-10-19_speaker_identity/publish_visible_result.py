"""Publish the actual test result to the board's visible sampling window."""
import base64
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
result=json.loads((HERE/'visible_capture_verification.json').read_text(encoding='utf-8'))
if result['status']=='PASS_WITHIN_SESSION_ONLY':
    score=result['query']['response']['result']['score']
    message='本次验证通过 · 相似度%.3f（实验门槛0.70）'%score
else:message='本次检查未通过，样本保留供排查，未降低门槛'
value={'message':message,'scope':'WITHIN_SESSION_ONLY','field_calibrated':False}
payload=base64.b64encode(json.dumps(value,ensure_ascii=False).encode()).decode('ascii')
script='''import base64,json,pathlib
directory=pathlib.Path.home()/'.local/share/aura/speaker_test_recordings'/SESSION
(directory/'verification_result.json').write_bytes(base64.b64decode(PAYLOAD))
print(json.dumps({'published':True,'session_id':SESSION}))
'''.replace('SESSION',repr(result['session_id'])).replace('PAYLOAD',repr(payload))
print(ssh('python3 -',script,timeout=10))
