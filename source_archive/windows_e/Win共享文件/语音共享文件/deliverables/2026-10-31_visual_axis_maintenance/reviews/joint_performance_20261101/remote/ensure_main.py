"""Read safe metadata and select the existing main page for the reviewed idle lifecycle."""
before,v,h=preflight()
if v.get('ui_page')!='main':command_page('main')
deadline=time.monotonic()+5
while True:
    v=get_json(8783,'/api/state');safe=assert_safe(v);avatar=v.get('avatar_display',{})
    ready=(safe['page']=='main' and avatar.get('visible') is True
           and avatar.get('frame_scheduling_active') is True and avatar.get('target_fps')==16)
    if ready or time.monotonic()>=deadline:break
    time.sleep(.2)
print(json.dumps(dict(status='MAIN_READY' if ready else 'MAIN_NOT_READY',before_state=before['state'],state=safe,
                      page_command_sent=before['state']['page']!='main',avatar=numeric(avatar))))
