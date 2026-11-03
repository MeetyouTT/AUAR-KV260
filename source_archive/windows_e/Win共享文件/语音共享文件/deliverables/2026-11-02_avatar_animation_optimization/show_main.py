# IMPORT_DEVICE_READ_HEADER
e=json.loads(Path(__file__).with_name('expected.json').read_bytes())
assert sha(P)==e['startup_sha256'] and owner(e['gui_owner']['pid'])==e['gui_owner'] and owner(e['camera_owner']['pid'])==e['camera_owner']
s=state();assert not s['playing'] and not s['pending_job'] and s['manual_pan']['automatic_following'] is False
assert s['handsfree_dialogue']['enabled'] is False and s['handsfree_dialogue']['microphone_open'] is False
before=s['ui_page'];sent=False
if before!='main':
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
 try:
  c.request('POST','/api/command',json.dumps({'type':'ui_page','page':'main'}),{'Content-Type':'application/json'})
  r=c.getresponse();raw=r.read(1048576);assert r.status==200;sent=True
 finally:c.close()
for _ in range(15):
 s=state()
 if s['ui_page']=='main' and s['avatar_display']['visible'] is True:break
 time.sleep(.2)
assert s['ui_page']=='main' and s['avatar_display']['visible'] is True
print(json.dumps(dict(status='MAIN_CHARACTER_VISIBLE',before_page=before,after_page=s['ui_page'],page_request_sent_once=sent,listening_enabled=s['handsfree_dialogue']['enabled'],no_audio_axis_camera_or_model_request=True)))
