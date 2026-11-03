import base64,json,urllib.parse,urllib.request
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/v1/ui/status',timeout=3) as f:s=json.load(f)
p=s['preview'];url='http://127.0.0.1:8790/v1/ui/preview.jpg?'+urllib.parse.urlencode({'camera_epoch':p['camera_epoch'],'frame_id':p['frame_id']})
with op.open(url,timeout=3) as f:raw=f.read()
assert len(raw)<400000
print(json.dumps({'private_image_base64':base64.b64encode(raw).decode(),'bytes':len(raw)}))
