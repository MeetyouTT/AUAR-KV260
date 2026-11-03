import base64,json,urllib.request,urllib.parse
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(path):
 with op.open('http://127.0.0.1:8790'+path,timeout=3) as f:return json.load(f)
s=get('/v1/ui/status');h=get('/health');ref=s.get('preview');assert ref
q=urllib.parse.urlencode({'camera_epoch':ref['camera_epoch'],'frame_id':ref['frame_id']})
with op.open('http://127.0.0.1:8790/v1/ui/preview.jpg?'+q,timeout=3) as f:raw=f.read(262145)
assert len(raw)<=262144
print(json.dumps({'scope':'READ_EXISTING_PREVIEW_ONLY_NO_NEW_CAMERA','private_biometric_image_do_not_share':True,'jpeg_base64':base64.b64encode(raw).decode(),'camera_pid':h['pid'],'capture_hz':h.get('capture_hz'),'detection_hz':h.get('detection_hz'),'face_count':s.get('modules',{}).get('identity',{}).get('face_count'),'face_health':h.get('identity',{}).get('face_targets')}))
