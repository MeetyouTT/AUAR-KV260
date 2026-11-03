"""Trace bounded local commands and the UI main-thread wait without restart."""
import base64,hashlib,json,subprocess,threading,time,urllib.error,urllib.request
from pathlib import Path

root=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
info=json.loads((root/'launch.json').read_text());base='http://127.0.0.1:8783'
rows=[];results=[];stop=threading.Event()
def sample():
    while not stop.wait(.1):
        try:
            with urllib.request.urlopen(base+'/api/state',timeout=1) as s:d=json.load(s)
            rows.append({'t':time.monotonic(),'seq':d['sequence'],'phase':d['phase'],
                'tick_ms':d.get('ui_tick_ms'),'wchan':Path('/proc/'+str(info['pid'])+'/wchan').read_text()})
        except Exception as e:rows.append({'error':str(e)})
thread=threading.Thread(target=sample);thread.start()
try:
    for command in ({'type':'save_evidence'},{'type':'preview_open'},{'type':'save_evidence'}):
        start=time.monotonic();record={'command':command}
        req=urllib.request.Request(base+'/api/command',data=json.dumps(command).encode(),
            headers={'Origin':base,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=8) as s:record['result']=json.load(s)
        except urllib.error.HTTPError as e:record.update(http_code=e.code,body=e.read().decode())
        except Exception as e:record['error']=str(e)
        record['elapsed_ms']=round((time.monotonic()-start)*1000,2);results.append(record);time.sleep(.4)
finally:
    stop.set();thread.join(2)
path=root/'response-probe.png'
capture=subprocess.run(['python3','-B',str(root/'aura/tools/board_screen_capture.py'),str(path)],
    env={'DISPLAY':':0','PATH':'/usr/bin:/bin'},stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5)
out={'results':results,'samples':rows,'capture_rc':capture.returncode}
if capture.returncode==0:
    import io
    from PIL import Image
    image=Image.open(path).convert('RGB');buf=io.BytesIO();image.save(buf,format='JPEG',quality=76);raw=buf.getvalue()
    out['screenshot']={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'width':image.width,'height':image.height,
        'jpeg_base64':base64.b64encode(raw).decode()}
print(json.dumps(out,ensure_ascii=False))
