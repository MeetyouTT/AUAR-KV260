import base64,json,urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def read(path):
 with o.open('http://127.0.0.1:8790'+path,timeout=3) as r:return r.read(150000)
s=json.loads(read('/v1/ui/status'));p=s['preview']
raw=read('/v1/ui/preview.jpg?camera_epoch='+p['camera_epoch']+'&frame_id='+str(p['frame_id']))
print(json.dumps(dict(preview_frame=p['frame_id'],camera_epoch=p['camera_epoch'],jpeg_base64=base64.b64encode(raw).decode(),motor_commands_sent=0,private_image_do_not_share=True)))
