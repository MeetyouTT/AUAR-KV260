import sys,json,base64
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]/'语音共享文件'
sys.path.insert(0,str(P/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
phase=sys.argv[1]
before=json.loads((H/'before.json').read_text(encoding='utf-8'))
runtime=before['board']['actual_runtime']+'/aura'
wav=P/'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav'
source=(H/'latency_probe.py').read_text(encoding='utf-8')
body=source.split("elif phase.startswith('test_'):\n",1)[1]
body='\n'.join(line[1:] if line.startswith(' ') else line for line in body.splitlines())
body=body.replace("wav=P/'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav'","wav=__import__('io').BytesIO(base64.b64decode('"+base64.b64encode(wav.read_bytes()).decode()+"'))")
body=body.replace("wave.open(str(wav),'rb')","wave.open(wav,'rb')").replace('wav.read_bytes()','wav.getvalue()')
body=body.replace("'residency':get('http://127.0.0.1:11435/api/ps')","'client':'board wired 192.168.50.2'")
prefix="import sys,json,time,hashlib,http.client,uuid,wave,base64,urllib.request\nsys.path.insert(0,"+repr(runtime)+")\nphase="+repr(phase)+"\ndef get(url):\n with urllib.request.urlopen(url,timeout=10) as r:return json.load(r)\ndef save(name,v):print(json.dumps(v))\n"
v=json.loads(ssh('python3 -B -',prefix+body,timeout=260))
(H/(phase+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(v,ensure_ascii=True))
