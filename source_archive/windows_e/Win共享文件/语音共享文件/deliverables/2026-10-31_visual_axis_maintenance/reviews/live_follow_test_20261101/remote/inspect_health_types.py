# USE_SESSION_COMMON
current_guard()
h=get_json(8790,'/health')
values={k:dict(type=type(h.get(k)).__name__,value=h.get(k) if type(h.get(k)) in (bool,int,float,type(None)) or h.get(k)=='' else 'NONEMPTY')
    for k in ('pid','camera_error','detector_error','capture_age_ms','detected_frames')}
values['identity']={k:dict(type=type(h['identity'].get(k)).__name__,
    value=h['identity'].get(k) if type(h['identity'].get(k)) in (bool,int,float,type(None)) or h['identity'].get(k)=='' else 'NONEMPTY')
    for k in ('ready','error','shutdown_incomplete','processed')}
print(json.dumps(dict(values=values,session_root_exists=ROOT.exists(),service=systemd(),services_changed=False)))
