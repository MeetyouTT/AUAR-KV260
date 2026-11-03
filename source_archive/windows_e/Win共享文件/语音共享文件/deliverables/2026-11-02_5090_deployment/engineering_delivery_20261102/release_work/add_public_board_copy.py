from common import *
import re
snap=load(ROOT/'board/config/startup.snapshot.json')
capture=load(W/'public_board_read_receipt.json')
units=load(W/'public_unit_copy.json')
pins=load(ROOT/'board/config/image_inputs.json')
assert all(x['state']=='match' for x in capture['files']) and len(capture['files'])==12
assert capture['gui_observation']['state']=='match' and all(x['eligible'] for x in units)
plan=load(ROOT/'board/config/deployment_files.json')
index={row['destination']:row['source'] for row in plan}
assert len(index)==len(plan)
fixed=load(ROOT/'data/reference/public_feedback.json')
cuenames={a['path'] for a in fixed['assets']}|{fixed['manifest']}
unit_sources={}
unit_groups={}
for u in units:
    n=u['destination']; group=u['unit'].split('-')[1]
    order=len(unit_groups.setdefault(u['unit'],[]))+1
    unit_groups[u['unit']].append(n)
    slug=re.sub(r'^(?:z+|\d+)-','',Path(n).name)
    unit_sources[n]='board/systemd/'+group+'/{:02d}_'.format(order)+slug
cam=load(ROOT/'board/config/original_camera_inputs.json')
previous=cam.get('recovered_from_kv260',cam['unresolved_from_offline_archives'])
records={}
def place(n,h,src,kind,expected):
    if n in records:
        assert records[n]['sha256']==h and records[n]['source']==src
        return
    blob=W/'public_kv260_copy'/h
    assert sha(blob)==h
    if n in index:assert index[n]==src and sha(ROOT/src)==h
    else:index[n]=src;plan.append(dict(source=src,destination=n))
    copy(blob,ROOT/src)
    records[n]={'source':src,'sha256':h,'bytes':blob.stat().st_size,'kind':kind,'hash_basis':expected}
for x in capture['files']:
    n=x['destination'];h=x['sha256'];assert pins['files'][n]==h
    if n in cuenames:src='board/public_cues/'+Path(n).name;kind='fixed_cue'
    elif n in unit_sources:src=unit_sources[n];kind='systemd_dropin'
    elif n.startswith('/etc/systemd/system/'):src='board/systemd/'+Path(n).name;kind='systemd_fragment'
    elif n.endswith('.so'):
        src=('board/camera_binaries/'+Path(n).name);kind='aarch64_shared_library'
        b=(W/'public_kv260_copy'/h).read_bytes();assert b.startswith(b'\x7fELF\x02\x01') and int.from_bytes(b[16:18],'little')==3 and int.from_bytes(b[18:20],'little')==183
    else:src='board/linked/'+h[:12]+'/'+Path(n).name;kind='camera_configuration'
    place(n,h,src,kind,'historical_pin')
for x in units:
    n=x['destination'];place(n,x['sha256'],unit_sources[n],'systemd_dropin','two_board_reads')
assert len(records)==len(set(pins['files'])|set(unit_sources))
meta={'schema':1,'source':'KV260 public release files, allowlisted SFTP-equivalent read via pinned SSH. No device writes or runtime operations.','captured_utc':capture['captured_utc'],'historical_pin_count':len(pins['files']),'systemd_dropin_count':len(units),'gui_file':{'source':'src/software/config/board_avatar_gtk.json','destination':capture['gui_path'],'sha256':capture['gui_observation']['sha256']},'systemd_order':unit_groups,'files':records}
save(ROOT/'board/config/public_board_resources.json',meta)
save(ROOT/'board/config/deployment_files.json',plan)
cam.update({'unresolved_from_offline_archives':{},'recovered_from_kv260':previous,'source':'Original camera metadata and baseline evidence. All seven former gaps now have byte-exact copies from the KV260; per-boot binding is still device-specific.'})
save(ROOT/'board/config/original_camera_inputs.json',cam)
pins.update({'purpose':'Twelve historical hashes. All original bytes now ship in this release; --image-root can additionally compare a separately mounted image.'})
save(ROOT/'board/config/image_inputs.json',pins)
save(QA/'board_public_copy.json',{'captured_utc':capture['captured_utc'],'result':'PASS','historical_pins_matched':len(capture['files']),'current_gui_matches_archived_sha256':True,'gui_and_business_bind_same_feedback_manifest':True,'firmware_or_service_actions':False,'microphone_or_speaker_used':False,'private_data_access':False,'fixed_wavs':[{k:x[k] for k in ('destination','sha256','bytes','samples','hz','channels','sample_width_bytes')} for x in capture['files'] if 'samples' in x],'current_systemd_dropins':{u:len(rows) for u,rows in unit_groups.items()},'unique_public_file_destinations':len(records),'package_evidence':'aura/board/config/public_board_resources.json'})
print('Public file map',len(records),'of which',len(pins['files']),'previously missing pins.',{u:len(v) for u,v in unit_groups.items()})
for u,paths in unit_groups.items():
    last=ROOT/records[paths[-1]]['source']
    print(u,[(key,val[:250]) for line in last.read_text(encoding='utf8').splitlines() if line.startswith(('ExecStart=','ExecStartPre=','WorkingDirectory=')) for key,_,val in [line.partition('=')] if val])
