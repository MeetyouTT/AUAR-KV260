"""Pinned ByteTrack companion update; reuse only verified prior payloads."""
import base64
import hashlib
import json
from pathlib import Path
import zipfile

WORK=Path(__file__).resolve().parent
REPO=Path('/home/ghmd/Win共享文件/共享文件夹/aura')
def sha(blob):return hashlib.sha256(blob).hexdigest()


def main():
    previous=json.loads((WORK/'manifest.json').read_text()) if (WORK/'manifest.json').exists() else None
    baseline=json.loads((WORK/'baseline/manifest.json').read_text())
    assert baseline['update_id']=='0da0dc7f7289d5b7'
    new=['board/vision/person_bytetrack.py','tests/framework/test_person_bytetrack.py',
         'config/board_camera_ui.yolo_iou.json','models/dpu/yolox_nano_person.prototxt']
    new+=['board/vision/bytetrack/'+p.name for p in sorted((REPO/'board/vision/bytetrack').iterdir()) if p.is_file()]
    runtime=list(baseline['runtime_files'])+['aura/'+p for p in new]
    files={name:(REPO/name[5:]).read_bytes() for name in runtime}
    old_config=Path('/home/ghmd/aura-board-yolo-20261011/startup/config.json')
    config=json.loads(old_config.read_text())
    for name,blob in files.items():
        if name!='aura/tools/board_avatar_gtk.py':config['component_sha256'][name[5:]]=sha(blob)
    config['gui_sha256']=sha(files['aura/tools/board_avatar_gtk.py'])
    launcher=(REPO/'scripts/board_ui_startup/launcher.py').read_bytes()
    configuration=(json.dumps(config,indent=2)+'\n').encode()
    release_id=sha(launcher+configuration)[:16]
    release='/home/root/aura-ui-startup-20261009/releases/'+release_id
    unit=(REPO/'scripts/board_ui_startup/aura-avatar-ui.service.in').read_text().replace('@INSTALL_DIR@',release).encode()
    files.update({'startup/launcher.py':launcher,'startup/config.json':configuration,'startup/aura-avatar-ui.service':unit})
    for name in ['board_apply.py','board_camera_control.py']:files[name]=(WORK/name).read_bytes()
    files['board_probe.py']=(WORK/'native_ui_probe.py').read_bytes()
    files['board_profile.py']=Path('/home/ghmd/aura-board-ui-design-20261009/board_preview_profile.py').read_bytes()
    files['board_status.py']=b'from pathlib import Path\nSTAGE=str(Path(__file__).resolve().parent.parent)\n'+(WORK/'board_status.py').read_bytes()
    files['board_acceptance.py']=(WORK/'board_acceptance.py').read_bytes()
    for name,blob in files.items():
        if name.endswith('.py'):compile(blob,name,'exec')
        if name.endswith('.json'):json.loads(blob)
    update_id=sha(b''.join(name.encode()+bytes.fromhex(sha(blob)) for name,blob in sorted(files.items())))[:16]
    stage='/home/root/aura-bytetrack-20261011/update-'+update_id
    seeds={name:'/home/root/aura-yolo-20261011/update-0da0dc7f7289d5b7/payload/'+name for name,blob in files.items()
           if baseline['files'].get(name,{}).get('sha256')==sha(blob)}
    if previous:
        for name,blob in files.items():
            if name not in seeds and previous['files'].get(name,{}).get('sha256')==sha(blob):
                seeds[name]='/home/root/aura-bytetrack-20261011/update-'+previous['update_id']+'/payload/'+name
    manifest={'kind':'AURA_BYTETRACK_PERSON_UI_UPDATE','update_id':update_id,
        'startup_release_id':release_id,'startup_release':release,
        'old_unit_sha256':baseline['files']['startup/aura-avatar-ui.service']['sha256'],
        'old_camera_unit_sha256':baseline['files']['aura/scripts/board_camera_ui/aura-camera-ui.service']['sha256'],
        'files':{name:{'bytes':len(blob),'sha256':sha(blob)} for name,blob in files.items()},
        'runtime_files':{name:{'before_sha256':baseline['files'].get(name,{}).get('sha256')} for name in runtime},
        'verified_board_seeds':seeds,'model_dependency':json.loads(files['aura/config/board_camera_ui.json'])['yolo']}
    payload=dict(files,**{'manifest.json':(json.dumps(manifest,indent=2)+'\n').encode()})
    paths=[]
    for label,names in [('update',set(payload)),('delta',set(payload)-set(seeds))]:
        path=WORK/('aura-bytetrack-'+label+'-'+update_id+'.zip')
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as stream:
            for name in sorted(names):
                info=zipfile.ZipInfo(name,date_time=(2026,10,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                stream.writestr(info,payload[name])
        with zipfile.ZipFile(path) as stream:
            assert stream.testzip() is None
            for name in names:assert stream.read(name)==payload[name]
        paths.append(path)
    meta={'archive':str(paths[0]),'bytes':paths[0].stat().st_size,'sha256':sha(paths[0].read_bytes()),
          'delta_archive':str(paths[1]),'delta_bytes':paths[1].stat().st_size,'delta_sha256':sha(paths[1].read_bytes()),
          'update_id':update_id,'startup_release_id':release_id,'runtime_files':len(runtime),'payload_files':len(files)}
    (WORK/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (WORK/'package_validation.json').write_text(json.dumps(meta,indent=2)+'\n')
    (WORK/'startup').mkdir(exist_ok=True)
    for name in ['launcher.py','config.json','aura-avatar-ui.service']:(WORK/'startup'/name).write_bytes(files['startup/'+name])
    encoded=base64.b64encode(paths[1].read_bytes()).decode()
    commands=[{'label':'prepare','source':'from pathlib import Path;Path('+repr(stage)+').mkdir(parents=True,exist_ok=True)'}]
    for index,start in enumerate(range(0,len(encoded),1500)):
        chunk=encoded[start:start+1500]
        source='from pathlib import Path;import hashlib\np=Path('+repr(stage+'/data.b64')+')\ns='+repr(chunk)+'\nn=p.stat().st_size if p.exists() else 0\nassert n>='+str(start)+'\n'
        source+='if n=='+str(start)+':\n with p.open("ab") as f:f.write(s.encode())\n'
        source+='assert hashlib.sha256(p.read_bytes()[:'+str(start+len(chunk))+']).hexdigest()=='+repr(sha(encoded[:start+len(chunk)].encode()))
        commands.append({'label':'chunk-%03d'%index,'source':source})
    source='STAGE='+repr(stage)+'\nSHA='+repr(meta['delta_sha256'])+'\n'+(WORK/'unpack.py').read_text()
    commands.append({'label':'verify','source':source})
    (WORK/'stage_commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    for name in ['probe','deploy','final','rollback']:
        source=(WORK/('board_'+name+'.py.in')).read_text().replace('@STAGE@',stage)
        (WORK/('board_'+name+'.py')).write_text(source)
    print(json.dumps(meta))


if __name__=='__main__':main()
