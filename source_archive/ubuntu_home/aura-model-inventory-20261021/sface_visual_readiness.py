import json,urllib.request
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8790/v1/ui/status',timeout=2) as r:s=json.load(r)
i=s.get('modules',{}).get('identity',{})
out={'scope':'READ_ONLY_COUNTS_ONLY_NO_IMAGE_IDENTITY_NAME_OR_EMBEDDING','source_kind':s.get('source_kind'),'face_count':i.get('face_count'),'single_face_target_available':bool(i.get('face_target')),'identity_state':i.get('state'),'identity_backend':i.get('backend')}
print(json.dumps(out))
