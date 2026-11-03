import json,subprocess,time
p=subprocess.Popen(['journalctl','-k','--since','20 minutes ago','-o','json','--no-pager'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
first=None;examined=0
try:
 for line in p.stdout:
  examined+=1
  try:r=json.loads(line)
  except ValueError:continue
  if "HC couldn't access mem fast enough for slot 4 ep 3" in r.get('MESSAGE',''):
   first={k:r.get(k) for k in ['__MONOTONIC_TIMESTAMP','__REALTIME_TIMESTAMP','MESSAGE']};break
  if examined>=2000:break
finally:
 p.terminate()
 try:p.wait(timeout=2)
 except subprocess.TimeoutExpired:p.kill();p.wait()
print(json.dumps({'scope':'First recorded matching warning in bounded journal search of past20min; not proof of first hardware fault',
 'examined_entries':examined,'first_matching':first,'now_mono_s':time.monotonic()}))
