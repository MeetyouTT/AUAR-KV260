"""No device/import/model/DB fixtures for full inspected assembly and staging."""
import copy
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import types
import wave
import zipfile

import pytest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('assembly_fixture',HERE/'assemble_v2.py')
assembly=importlib.util.module_from_spec(spec);spec.loader.exec_module(assembly)


def wav(rate=24000):
    out=io.BytesIO()
    with wave.open(out,'wb') as value:
        value.setnchannels(1);value.setsampwidth(2);value.setframerate(rate);value.writeframes(bytes(2400*2))
    return out.getvalue()


class Files:
    def __init__(self):self.data={};self.alias={};self.dirs=set();self.writes=[];self.reads=[]
    def info(self,name,canonical=False):
        target=self.alias.get(name,name)
        if canonical:assembly.need(target==name,'source_path_redirected')
        if target not in self.data:raise FileNotFoundError(name)
        return {'bytes':len(self.data[target]),'resolved':target}
    def read(self,name,limit=16*1024*1024,canonical=False):
        assert name!='/PRIVATE_DB_MUST_NEVER_READ'
        self.reads.append(name);info=self.info(name,canonical=canonical)
        assembly.need(info['bytes']<=limit,'source_too_large');return self.data[info['resolved']]
    def hash(self,name):return assembly.digest(self.read(name,1024*1024*1024))
    def tree(self,root):
        return {name[len(root)+1:]:{'bytes':len(raw),'sha256':assembly.digest(raw)}
                for name,raw in sorted(self.data.items()) if name.startswith(root+'/')}
    def exists(self,name):return name in self.data or name in self.dirs
    def create_root(self,name):
        assembly.need(not self.exists(name),'target_already_exists');self.dirs.add(name)
    def directory(self,name):self.dirs.add(name)
    def write(self,name,raw):
        assembly.need(not self.exists(name),'exclusive_write_refused');self.data[name]=raw;self.writes.append(name)


@pytest.fixture
def env():
    p=json.loads((HERE/'assembly_policy.v2.final.json').read_text(encoding='utf-8'));files=Files()
    actual=json.loads((HERE/'actual_public_configuration.json').read_text(encoding='utf-8'))
    startup,gui=copy.deepcopy(actual['startup']['content']),copy.deepcopy(actual['gui']['content'])
    for name in p['baseline']['pins']:
        path=assembly.join(p['baseline']['runtime']+'/aura',name)
        files.data[path]=('public component fixture '+name).encode()
    for name in ['ui/ui_layout_spec.json','ui/ui_tokens.json','ui/board_touch_layout.json',
                 'common/schemas/board_ui_snapshot.schema.json','common/schemas/board_ui_command.schema.json',
                 'common/schemas/board_ui_ack.schema.json']:
        files.data[assembly.join(p['baseline']['runtime']+'/aura',name)]=assembly.encoded({'public_fixture':True})
    files.data[assembly.join(p['baseline']['runtime']+'/aura','config/board_ui_services.json')]=assembly.encoded(
        {'schema_version':'aura-ui-1','connection':{'enabled':False,'host':'127.0.0.1','port':8790}})
    files.data[p['baseline']['gui']]=assembly.encoded(gui)
    files.data[assembly.join(p['baseline']['runtime']+'/aura','tools/board_avatar_pan.py')]=(
        HERE.parent/'resume_yuki_business_candidate_v2/candidate/aura/tools/board_avatar_pan.py').read_bytes()
    for name in ('pan_manual.local.json','pan_face.local.json','pan_direction.current.json'):
        files.data[assembly.join(p['baseline']['runtime']+'/aura','config/'+name)]=assembly.encoded(
            {'fixture_protected_metadata':True,'boot_id':'original unchanged boot','fdt_sha256':'a'*64,
             'face_follow_config':'/original/protected/follow.json','enabled':True})
    p['baseline']['pins']={name:files.hash(assembly.join(p['baseline']['runtime']+'/aura',name)) for name in p['baseline']['pins']}
    startup['component_sha256']=p['baseline']['pins'];files.data[p['baseline']['startup']]=assembly.encoded(startup)
    p['baseline']['startup_sha256']=files.hash(p['baseline']['startup']);p['baseline']['gui_sha256']=files.hash(p['baseline']['gui'])
    reference=wav();selection={'reference_audio':'reference/soft_young.wav','reference_sha256':assembly.digest(reference),'reference_text':'Public selected voice fixture'}
    for row in p['public_copies']:
        if row['target'].endswith('selection.json'):raw=assembly.encoded(selection)
        elif row['target'].endswith('base_model_verification.json'):raw=assembly.encoded({'revision':'accepted-original-reference'})
        elif row['target'].endswith('.wav'):raw=reference
        elif row['target'].endswith('.ttf'):raw=b'public-font-fixture'
        elif row['target'].endswith('.html'):raw='<html><title>夕岚 controls</title></html>'.encode()
        else:raw=b'public-javascript-fixture'
        files.data[row['source']]=raw;files.alias[row['declared']]=row['source']
        row.update(bytes=len(raw),sha256=assembly.digest(raw))
    sm={'schema_version':1,'sample_rate':16000,'dimension':192,'precision':'float32','source_model_id':'ecapa-original-fixture'}
    for row in p['models']:
        raw=assembly.encoded(sm) if row['path']==p['speaker_directory']+'/manifest.json' else ('public same model fixture '+row['path']).encode()
        files.data[row['path']]=raw;row.update(bytes=len(raw),sha256=assembly.digest(raw))
    p['speaker_manifest_sha256']=files.hash(p['speaker_directory']+'/manifest.json')
    elf=b'\x7fELF\x02\x01'+bytes(12)+(183).to_bytes(2,'little')+bytes(20)
    for d in p['dependencies']:
        if d['kind']=='numpy':files.data[d['root']+'/version.py']=b"version = '1.21.2'\n"
        else:
            name=d['kind'].replace('-','_')+'-'+d['version']+'.dist-info/METADATA'
            files.data[d['root']+'/'+name]=('Name: '+d['kind']+'\nVersion: '+d['version']+'\n').encode()
            files.data[d['root']+'/package/__init__.py']=b'# pinned public package fixture\n'
        files.data[d['root']+'/native.so']=elf
    face={'board_boot_id':p['camera']['boot'],'camera_pid':p['camera']['pid'],
          'camera_start_ticks':p['camera']['birth'],'database':'/PRIVATE_DB_MUST_NEVER_READ'}
    files.data[p['face_readback']['path']]=assembly.encoded(face);p['face_readback']['sha256']=files.hash(p['face_readback']['path'])
    value={'version':1,'assets':{}}
    for name,text in [('thinking','让我想一想。'),('arrival','你好，我是雪妃。'),('invitation','想聊聊时叫我雪妃。')]:
        source=str(PurePosixPath(p['feedback']['path']).parent/(name+'.wav'));audio=wav();files.data[source]=audio
        value['assets'][name]={'path':source,'metadata':{'protocol':'aura-voice-1','source_kind':'actual','engine':'omnivoice',
            'num_step':16,'revision':'c5fdb5ccb189668d56333f77ba2629f4cd7535f4','reply_text':text,'emotion':'neutral',
            'bytes':len(audio),'sha256':assembly.digest(audio),'duration_seconds':.1}}
    files.data[p['feedback']['path']]=assembly.encoded(value);p['feedback']['sha256']=files.hash(p['feedback']['path'])
    archive='/public/v2.zip'
    files.data[archive]=(HERE.parent/'resume_yuki_business_candidate_v2/yuki_business.source_candidate.zip').read_bytes()
    return types.SimpleNamespace(p=p,f=files,archive=archive,target=p['target_root_prefix']+'fixture',bounds=[1793404800,1793577600])


def inspect(e):return assembly.inspect(e.p,e.archive,e.target,e.bounds,files=e.f)


def test_v2_full_inspect_is_inert_and_new_synthetic_config_preserves_all_boundary_choices(env):
    before=copy.deepcopy(env.f.data);plan,payload=inspect(env)
    assert plan['ready'] and env.f.data==before and env.f.writes==[]
    cfg=assembly.parse(payload['runtime/aura/config/board_avatar_gtk.json'])
    assert cfg['board_business']['data_origin']=='synthetic' and cfg['board_business']['private_root'].startswith(env.target+'/private/')
    assert cfg['board_business']['model_port']==8797 and cfg['audio_frontend'] is None
    assert cfg['portrait_offload']=={'enabled':False} and cfg['native_yuki']['fps']==16
    assert cfg['board_business']['speaker']['expected_model_id']=='ecapa-original-fixture'
    assert cfg['board_business']['face_readback']==env.p['face_readback']
    assert plan['source']['archive_sha256']=='2c25b6a91a635a9bb70eef00cdc180829c503cdba3382135f8366c72e3242334'
    assert plan['launch']['microphone_initially_enabled'] is False and plan['launch']['following_initially_enabled'] is False
    assert plan['launch']['environment']['HOME']==env.target+'/private/home'
    assert plan['launch']['environment']['PYTHONPYCACHEPREFIX']==env.target+'/private/pycache'
    assert plan['launch']['command'][0:2]==['/usr/bin/python3','-B']
    assert all('assets/avatar/' not in n for n in payload)
    assert {n for n in payload if '.local.' in n}=={'runtime/aura/config/pan_manual.local.json','runtime/aura/config/pan_face.local.json'}
    assert all(env.p['face_readback']['path'] not in n for n in payload)
    assert '/PRIVATE_DB_MUST_NEVER_READ' not in env.f.reads
    assert '夕岚' not in payload['stage/index.html'].decode()
    assert plan['public_browser_title_transform']['scope'].startswith('one existing browser title')
    assert plan['launch']['command'][2].endswith('/tools/board_avatar_pan.py')
    startup=assembly.parse(payload['startup/config.json'])
    assert startup['runtime']==env.target+'/runtime'
    for name in ('pan_manual.local.json','pan_face.local.json','pan_direction.current.json'):
        raw=payload['runtime/aura/config/'+name]
        original=assembly.join(env.p['baseline']['runtime']+'/aura','config/'+name)
        assert raw==env.f.data[original]
        assert startup['component_sha256']['config/'+name]==assembly.digest(raw)


def test_stage_creates_only_new_tree_and_does_not_link_or_overwrite_old_resources(env,monkeypatch):
    plan,payload=inspect(env);old=copy.deepcopy(env.f.data)
    monkeypatch.setattr(assembly,'os',types.SimpleNamespace(name='posix',geteuid=lambda:0))
    result=assembly.stage(plan,payload,plan['inspection_sha256'],files=env.f)
    assert result['status']=='SYNTHETIC_RUNTIME_STAGED_NOT_STARTED'
    assert all(env.f.data[k]==v for k,v in old.items())
    assert all(n.startswith(env.target+'/') for n in env.f.writes)
    assert not any('key' in PurePosixPath(n).name or n.endswith(('.sqlite','.db')) for n in env.f.writes)
    with pytest.raises(assembly.Refused):assembly.stage(plan,payload,plan['inspection_sha256'],files=env.f)


@pytest.mark.parametrize('bounds',[None,[1620000000,1620086400],[1,1],[1793404800,float('nan')],[1793404800,1794404800]])
def test_missing_or_old_board_wall_utc_never_stages(env,monkeypatch,bounds):
    env.bounds=bounds;plan,payload=inspect(env)
    assert not plan['ready'] and plan['missing_runtime_fields']
    monkeypatch.setattr(assembly,'os',types.SimpleNamespace(name='posix',geteuid=lambda:0))
    with pytest.raises(assembly.Refused):assembly.stage(plan,payload,plan['inspection_sha256'],files=env.f)
    assert env.f.writes==[]


@pytest.mark.parametrize('case',['startup','gui','component','model','font','ancestor','face','ecapa_manifest'])
def test_actual_baseline_and_explicit_public_or_private_metadata_changes_refuse_without_writes(env,case):
    if case=='startup':path=env.p['baseline']['startup']
    elif case=='gui':path=env.p['baseline']['gui']
    elif case=='component':path=assembly.join(env.p['baseline']['runtime']+'/aura','tools/board_recording.py')
    elif case=='model':path=env.p['models'][0]['path']
    elif case=='font':path=next(r['source'] for r in env.p['public_copies'] if r['target'].endswith('.ttf'))
    elif case=='face':path=env.p['face_readback']['path']
    elif case=='ecapa_manifest':path=env.p['speaker_directory']+'/manifest.json'
    elif case=='ancestor':
        row=env.p['public_copies'][0];env.f.alias[row['declared']]=row['source']+'.other';env.f.data[row['source']+'.other']=env.f.data[row['source']]
        path=None
    if path:env.f.data[path]+=b'changed'
    with pytest.raises((assembly.Refused,ValueError)):inspect(env)
    assert not env.f.writes


@pytest.mark.parametrize('case',['old_name','steps','revision','wave_rate','duration','remove_thinking'])
def test_public_feedback_must_retain_actual_accepted_voice_and_paired_character(env,case):
    value=assembly.parse(env.f.data[env.p['feedback']['path']]);row=value['assets']['thinking'];meta=row['metadata']
    if case=='old_name':meta['reply_text']='我是夕岚。'
    if case=='steps':meta['num_step']=8
    if case=='revision':meta['revision']='unreviewed'
    if case=='wave_rate':
        raw=wav(16000);env.f.data[row['path']]=raw;meta.update(sha256=assembly.digest(raw),bytes=len(raw))
    if case=='duration':meta['duration_seconds']=10
    if case=='remove_thinking':del value['assets']['thinking']
    env.f.data[env.p['feedback']['path']]=assembly.encoded(value);env.p['feedback']['sha256']=env.f.hash(env.p['feedback']['path'])
    with pytest.raises(assembly.Refused):inspect(env)
    assert env.f.writes==[]


@pytest.mark.parametrize('case',['version','architecture'])
def test_dependency_metadata_and_arm_architecture_refused_without_import(env,case):
    root=env.p['dependencies'][0]['root']
    if case=='version':
        name=next(k for k in env.f.data if k.startswith(root+'/') and k.endswith('METADATA'))
        env.f.data[name]=env.f.data[name].replace(b'1.17.3',b'1.19.2')
    else:env.f.data[root+'/native.so']=b'foreign x86 binary'
    with pytest.raises(assembly.Refused):inspect(env)


def test_dependency_tree_change_requires_new_explicit_inspection_token(env,monkeypatch):
    plan,payload=inspect(env)
    env.f.data[env.p['dependencies'][0]['root']+'/package/extra.py']=b'# new cached source'
    again,data=inspect(env);assert again['inspection_sha256']!=plan['inspection_sha256']
    monkeypatch.setattr(assembly,'os',types.SimpleNamespace(name='posix',geteuid=lambda:0))
    with pytest.raises(assembly.Refused):assembly.stage(again,data,plan['inspection_sha256'],files=env.f)
    assert not env.f.writes


@pytest.mark.parametrize('bad',['../escape.py','/abs.py','a\\b.py','aura/.venv/secret.py','aura/config/control.local.json','weights.onnx','secret.db'])
def test_untrusted_archive_path_or_private_file_refused_even_with_matching_outer_hash(bad):
    raw=io.BytesIO()
    with zipfile.ZipFile(raw,'w') as z:
        z.writestr(bad,b'bad');z.writestr('manifest.json',b'{}')
    data=raw.getvalue()
    if bad=='a\\b.py':data=data.replace(b'a/b.py',b'a\\b.py')  # Windows zip writer normalizes os.sep first.
    p={'source':{'archive_bytes':len(data),'archive_sha256':assembly.digest(data),'files':2}}
    with pytest.raises(assembly.Refused):assembly.zip_payload(data,p)


def test_archive_symlink_and_duplicate_entries_refused_before_extraction():
    raw=io.BytesIO()
    with zipfile.ZipFile(raw,'w') as z:
        info=zipfile.ZipInfo('aura/tools/linked.py');info.create_system=3;info.external_attr=0o120777<<16
        z.writestr(info,b'/old/private');z.writestr('manifest.json',b'{}')
    data=raw.getvalue();p={'source':{'archive_bytes':len(data),'archive_sha256':assembly.digest(data),'files':2}}
    with pytest.raises(assembly.Refused):assembly.zip_payload(data,p)


def test_new_config_requires_current_model_descriptors_but_never_copies_models(env):
    plan,payload=inspect(env)
    assert len(plan['models'])==7 and all('.onnx' not in n and '.npz' not in n for n in payload)
    refs=assembly.parse(payload['resource_refs.json'],10*1024*1024)
    assert refs['read_only_references'] and refs['face_readback']==env.p['face_readback']
    assert refs['dependencies'][0]['version']=='1.17.3'
