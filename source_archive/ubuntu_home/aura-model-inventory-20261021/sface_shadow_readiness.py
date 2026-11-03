import json,time,urllib.request
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
out={'windows_health':{},'scope':'READ_ONLY_NO_FEATURE_AUDIO_OR_ENROLLMENT_REQUEST'}
for route in ['/health']:
    start=time.monotonic()
    try:
        with opener.open('http://192.168.50.1:8792'+route,timeout=2) as r:s=json.load(r)
        out['windows_health'][route]={'reachable':True,'top_keys':sorted(s)[:40],'status':s.get('status'),'seconds':time.monotonic()-start}
    except Exception as e:out['windows_health'][route]={'reachable':False,'error_type':type(e).__name__,'seconds':time.monotonic()-start}
with opener.open('http://127.0.0.1:8790/health',timeout=2) as r:s=json.load(r)
out['camera']={k:s.get(k) for k in ['pid','detection_hz','camera_error','detector_error']}
out['camera']['identity_backend']=s.get('identity',{}).get('backend')
print(json.dumps(out))
