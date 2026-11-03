import base64,json,urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8790/v1/ui/status',timeout=3) as r:s=json.load(r)
p=s['preview'];url='http://127.0.0.1:8790/v1/ui/preview.jpg?camera_epoch='+p['camera_epoch']+'&frame_id='+str(p['frame_id'])
with o.open(url,timeout=3) as r:raw=r.read(150000)
print(json.dumps({'jpeg_base64':base64.b64encode(raw).decode(),'width':640,'height':480}))
