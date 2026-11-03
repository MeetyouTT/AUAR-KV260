import json,subprocess,urllib.request,time
out={'interfaces':json.loads(subprocess.check_output(['ip','-j','address'])),'route':subprocess.check_output(['ip','route']).decode()}
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 with opener.open('http://172.23.232.155:34023/aura-dpu-vision-preflight',timeout=5) as r:
  out['host_fetch_verified']=r.read(100)==b'aura-dpu-network-check'
except Exception as e:out['host_fetch_verified']=False;out['error']=str(e)
print(json.dumps(out))
