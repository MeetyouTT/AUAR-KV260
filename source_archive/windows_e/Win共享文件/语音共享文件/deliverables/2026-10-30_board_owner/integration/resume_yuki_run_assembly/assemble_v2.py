"""Inspect by default; explicitly stage a complete isolated synthetic GUI tree.

No GUI/audio/native/dependency import, service request, package install or
process start is performed here. Root controls any later GUI trial separately.
"""
import argparse
import ast
from email.parser import BytesParser
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import wave
import zipfile


class Refused(RuntimeError):pass
def need(value,code):
    if not value:raise Refused(code)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(value):return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None
def encoded(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def unique(pairs):
    result={}
    for k,v in pairs:need(k not in result,'duplicate_json_key');result[k]=v
    return result
def parse(raw,limit=262144):
    need(len(raw)<=limit,'metadata_too_large')
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(Refused('nonfinite_json')))
def relative(name):
    path=PurePosixPath(name)
    need(isinstance(name,str) and name and not path.is_absolute() and '..' not in path.parts
         and str(path)==name and '\\' not in name and ':' not in name,'unsafe_relative_path')
    return path
def join(root,name):return str(PurePosixPath(root)/relative(name))


class Files:
    def info(self,name,*,canonical=False):
        path=Path(name)
        need(path.is_absolute() and path.is_file(),'source_not_regular_file')
        if canonical:need(not path.is_symlink() and path.resolve()==path,'source_path_redirected')
        return {'bytes':path.stat().st_size,'resolved':str(path.resolve())}
    def read(self,name,limit=16*1024*1024,*,canonical=False):
        need(self.info(name,canonical=canonical)['bytes']<=limit,'source_too_large')
        return Path(name).read_bytes()
    def hash(self,name):
        self.info(name)
        value=hashlib.sha256()
        with Path(name).open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
        return value.hexdigest()
    def tree(self,root):
        path=Path(root);need(path.is_absolute() and not path.is_symlink() and path.resolve()==path and path.is_dir(),'dependency_root_redirected')
        result={};total=0
        for item in sorted(path.rglob('*')):
            need(not item.is_symlink(),'dependency_symlink_refused')
            if not item.is_file():continue
            name=str(item.relative_to(path)).replace('\\','/')
            if '__pycache__' in item.parts or item.suffix in ('.pyc','.pyo'):continue
            need(item.suffix.lower() not in ('.gguf','.safetensors','.sqlite','.sqlite3','.db','.key','.pem','.pth'),
                 'foreign_or_private_dependency_file')
            total+=item.stat().st_size;need(total<=256*1024*1024 and len(result)<5000,'dependency_tree_budget')
            result[name]={'bytes':item.stat().st_size,'sha256':self.hash(str(item))}
        need(result,'empty_dependency_tree');return result
    def exists(self,name):return os.path.lexists(name)
    def create_root(self,name):
        path=Path(name);need(not self.exists(name) and path.parent.resolve()==path.parent,'new_canonical_target_required')
        info=path.parent.stat();need(info.st_uid==0 and stat.S_ISDIR(info.st_mode),'root_owned_target_parent_required')
        path.mkdir(mode=0o700)
    def directory(self,name):
        path=Path(name)
        if not path.exists():
            self.directory(str(path.parent));path.mkdir(mode=0o700)
        need(path.resolve()==path and not path.is_symlink(),'new_directory_redirected')
        info=path.stat();need(info.st_uid==0 and not info.st_mode&0o077,'new_directory_not_private')
    def write(self,name,raw):
        self.directory(str(Path(name).parent))
        fd=os.open(name,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
        with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())


def zip_payload(raw,policy):
    source=policy['source'];need(len(raw)==source['archive_bytes'] and digest(raw)==source['archive_sha256'],'source_archive_sha_or_size_changed')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries=archive.infolist();names=[row.filename for row in entries]
        need(len(entries)==source['files'] and len(set(names))==len(names)
             and len({n.casefold() for n in names})==len(names),'archive_file_count_or_duplicates')
        total=0
        for row in entries:
            need(row.orig_filename==row.filename,'archive_path_normalization_refused')
            relative(row.filename);mode=row.external_attr>>16
            need(not row.is_dir() and stat.S_IFMT(mode) in (0,stat.S_IFREG) and not row.flag_bits&1,'archive_special_file')
            need(row.file_size<=16*1024*1024,'archive_member_budget');total+=row.file_size
            need(total<=64*1024*1024,'archive_total_budget')
            need(row.filename.endswith(('.py','.json','.txt','.patch','.png','.so')),'unexpected_archive_type')
            need(not any(x in PurePosixPath(row.filename).parts for x in ('cache','__pycache__','venv','.venv'))
                 and '.local.' not in row.filename and not row.filename.endswith(('.onnx','.npz')),'private_or_model_archive_file')
        manifest_raw=archive.read('manifest.json');need(digest(manifest_raw)==source['manifest_sha256'],'source_manifest_changed')
        manifest=parse(manifest_raw,262144)
        need(source.get('candidate_revision')==2 and manifest.get('candidate_revision')==2
             and manifest.get('schema')=='aura.yuki.board_business.source_candidate.v1'
             and manifest.get('business_data_included') is False and manifest.get('model_weights_included') is False
             and set(manifest['files'])|{'manifest.json'}==set(names),'source_manifest_closure_mismatch')
        result={}
        for row in entries:
            data=archive.read(row)
            if row.filename!='manifest.json':
                pin=manifest['files'][row.filename]
                need(pin=={'sha256':digest(data),'bytes':len(data)},'source_member_changed')
            result[row.filename]=data
        need(sum(n.endswith('.py') for n in names)==source['python_files'],'python_count_changed')
        return result,manifest


def numpy_version_metadata(spec,files):
    """Static data only: never import/exec NumPy or Versioneer source."""
    expected=spec['version'];need(expected=='1.21.2','original_numpy_1212_required')
    version_path=join(spec['root'],'version.py')
    raw=files.read(version_path,65536,canonical=True)
    module=ast.parse(raw.decode('utf-8'))
    assignments={}
    for node in module.body:
        if isinstance(node,ast.Assign):targets=node.targets;value=node.value
        elif isinstance(node,ast.AnnAssign):targets=[node.target];value=node.value
        else:continue
        for target in targets:
            if isinstance(target,ast.Name) and target.id in ('version','full_version'):
                need(target.id not in assignments,'ambiguous_numpy_version_assignment')
                assignments[target.id]=value
    literal=assignments.get('version')
    if isinstance(literal,ast.Constant) and isinstance(literal.value,str):
        need(literal.value==expected,'numpy_version_metadata_changed')
        if 'full_version' in assignments:
            full=assignments['full_version']
            need(isinstance(full,ast.Constant) and full.value==expected,'conflicting_numpy_full_version')
        return {'kind':'static_literal','version':expected,'sources':{version_path:digest(raw)}}
    # This is the exact already-running board vendor wrapper, not a generic
    # permission to resolve arbitrary imports, calls or dynamic expressions.
    need(spec['root']=='/usr/lib/python3.9/site-packages/numpy'
         and digest(raw)=='f89c73ddd072eb0eb166095f2b8238bfb0a7baec6f1a63545e8e42ad55ba2314',
         'unreviewed_numpy_versioneer_wrapper')
    source_path=join(spec['root'],'_version.py')
    source=files.read(source_path,65536,canonical=True)
    need(digest(source)=='db1df0c97f67f72e474f2dbd77e4a2b049727c20e556fd1c24e988d41dbf3841',
         'reviewed_numpy_versioneer_source_changed')
    body=ast.parse(source.decode('utf-8')).body
    need(len(body)==3 and isinstance(body[0],ast.Import)
         and [(a.name,a.asname) for a in body[0].names]==[('json',None)]
         and isinstance(body[1],ast.Assign) and len(body[1].targets)==1
         and isinstance(body[1].targets[0],ast.Name) and body[1].targets[0].id=='version_json'
         and isinstance(body[1].value,ast.Constant) and isinstance(body[1].value.value,str),
         'numpy_versioneer_static_literal_required')
    expected_function=ast.parse('def get_versions():\n    return json.loads(version_json)\n').body[0]
    need(ast.dump(body[2],include_attributes=False)==ast.dump(expected_function,include_attributes=False),
         'numpy_versioneer_dynamic_function_refused')
    info=parse(body[1].value.value.encode('utf-8'))
    need(info.get('version')==expected and info.get('dirty') is False and info.get('error') is None,
         'numpy_versioneer_version_not_exact_1212')
    pkg_path=str(PurePosixPath(spec['root']).parent/'numpy-1.21.2-py3.9.egg-info/PKG-INFO')
    pkg=files.read(pkg_path,65536,canonical=True)
    need(digest(pkg)=='c29a04ebcd5571a84b995ceb79ab86f89bde0f8a0b5413c81c357ab72ed15352',
         'reviewed_numpy_egg_metadata_changed')
    metadata=BytesParser().parsebytes(pkg)
    need(metadata.get_all('Name')==['numpy'] and metadata.get_all('Version')==[expected],
         'numpy_versioneer_egg_version_mismatch')
    return {'kind':'reviewed_static_versioneer_and_egg','version':expected,
            'sources':{version_path:digest(raw),source_path:digest(source),pkg_path:digest(pkg)}}


def dependency(spec,files):
    tree=files.tree(spec['root']);version=spec['version'];kind=spec['kind']
    if kind!='numpy':
        need(not any(name=='numpy.py' or name.startswith('numpy/') for name in tree),
             'non_baseline_numpy_shadow_in_dependency_root')
    version_evidence=None
    if kind=='numpy':
        version_evidence=numpy_version_metadata(spec,files)
    else:
        found=False
        for name in tree:
            if name.endswith('.dist-info/METADATA'):
                text=files.read(join(spec['root'],name),65536).decode()
                fields=dict(line.split(': ',1) for line in text.splitlines() if ': ' in line)
                package=fields.get('Name','').lower().replace('_','-')
                if package==kind:
                    need(fields.get('Version')==version,'dependency_version_changed');found=True
        need(found,'dependency_distribution_metadata_missing')
    for name in tree:
        if '.so' in PurePosixPath(name).name:
            header=files.read(join(spec['root'],name),64*1024*1024)[:20]
            need(header[:6]==b'\x7fELF\x02\x01' and int.from_bytes(header[18:20],'little')==183,
                 'dependency_native_architecture_changed')
    result={'kind':kind,'version':version,'root':spec['root'],'files':tree,'tree_sha256':digest(encoded(tree))}
    if version_evidence is not None:result['version_metadata']=version_evidence
    return result


def checked_copy(files,row):
    info=files.info(row['source'],canonical=True)
    need(info['bytes']==row['bytes'] and info['resolved']==row['source']
         and files.hash(row['source'])==row['sha256'],'public_resource_changed')
    # Original logical ancestor links are inspected only, never re-created.
    if row.get('declared'):
        need(files.info(row['declared'])['resolved']==row['source'],'public_ancestor_binding_changed')
    need(PurePosixPath(row['target']).suffix.lower() in ('.json','.ttf','.wav','.html','.js'),'public_copy_type_not_allowed')
    return files.read(row['source'],16*1024*1024,canonical=True)


def feedback(files,spec,target):
    raw=files.read(spec['path'],65536,canonical=True);need(digest(raw)==spec['sha256'],'approved_feedback_manifest_changed')
    value=parse(raw);need(set(value)=={'version','assets'} and value['version']==1
                         and 'thinking' in value['assets'] and not set(value['assets'])-{'thinking','arrival','invitation'},'approved_feedback_required')
    payload={};result={'version':1,'assets':{}}
    for kind,row in value['assets'].items():
        need(set(row)=={'path','metadata'},'feedback_entry_schema')
        meta=row['metadata'];text=meta.get('reply_text')
        need(meta.get('protocol')=='aura-voice-1' and meta.get('source_kind')=='actual'
             and meta.get('engine')=='omnivoice' and meta.get('num_step')==16
             and meta.get('revision')=='c5fdb5ccb189668d56333f77ba2629f4cd7535f4'
             and isinstance(text,str) and text.strip() and len(text)<=240 and '\u5915\u5c9a' not in text
             and all(ord(c)>=32 for c in text) and meta.get('emotion') in ('neutral','friendly','happy','sad'),
             'approved_voice_or_character_metadata_changed')
        audio=files.read(row['path'],1500000,canonical=True)
        need(type(meta.get('bytes')) is int and len(audio)==meta['bytes'] and digest(audio)==meta.get('sha256'),'feedback_wav_hash_changed')
        with wave.open(io.BytesIO(audio),'rb') as wav:
            duration=wav.getnframes()/24000
            need((wav.getframerate(),wav.getnchannels(),wav.getsampwidth())==(24000,1,2)
                 and 0<duration<=5 and type(meta.get('duration_seconds')) in (int,float)
                 and abs(duration-meta['duration_seconds'])<=1/24000
                 and len(wav.readframes(wav.getnframes()))==wav.getnframes()*2,'feedback_pcm_contract_changed')
        name='runtime/public_cues/'+kind+'.wav';payload[name]=audio
        result['assets'][kind]={'path':join(target,name),'metadata':copy.deepcopy(meta)}
    payload['runtime/public_cues/feedback.json']=encoded(result)
    return payload


def inspect(policy,archive,target,utc_bounds,*,files=None):
    files=files or Files();need(policy.get('schema')=='aura-yuki-synthetic-assembly-policy-1','unsupported_assembly_policy')
    need(target.startswith(policy['target_root_prefix']) and str(PurePosixPath(target))==target
         and '..' not in PurePosixPath(target).parts,'new_private_target_prefix_required')
    need(not files.exists(target),'target_already_exists_no_merge_or_overwrite')
    baseline=policy['baseline'];startup_raw=files.read(baseline['startup']);gui_raw=files.read(baseline['gui'])
    need(digest(startup_raw)==baseline['startup_sha256'] and digest(gui_raw)==baseline['gui_sha256'],'actual_r3_configuration_changed')
    startup,gui=parse(startup_raw),parse(gui_raw)
    need(startup['runtime']==baseline['runtime'] and startup['component_sha256']==baseline['pins']
         and len(baseline['pins'])==286,'actual_r3_component_selection_changed')
    sources={}
    for name,expected in baseline['pins'].items():
        path=join(baseline['runtime']+'/aura',name)
        need(files.hash(path)==expected,'actual_r3_component_hash_changed')
        sources[path]={'sha256':expected,'resolved':files.info(path)['resolved']}
    payload,manifest=zip_payload(files.read(archive,8*1024*1024),policy)
    payload={'runtime/'+name:raw for name,raw in payload.items()}
    for row in policy['public_copies']:
        name=row['target'];relative(name);need(name not in payload,'public_copy_would_override_frozen_source')
        payload[name]=checked_copy(files,row)
    voice='runtime/deliverables/2026-10-06_voice_selected_soft_young/'
    selection=parse(payload[voice+'selection.json'])
    reference=voice+str(relative(selection['reference_audio']))
    need(reference in payload and digest(payload[reference])==selection['reference_sha256']
         and isinstance(selection.get('reference_text'),str),'selected_voice_reference_binding_changed')
    need(isinstance(parse(payload[voice+'base_model_verification.json']).get('revision'),str),
         'selected_voice_public_revision_missing')
    # New browser title is paired metadata only. The original public file and
    # every audio/reference transcript remain byte-exact at their source.
    title_transform=None
    if 'stage/index.html' in payload:
        original=payload['stage/index.html'];text=original.decode('utf-8')
        display=parse(payload['runtime/aura/config/persona.xuefei.candidate.json'])['display_name']
        text,count=re.subn(r'(<title>[^<]*)\u5915\u5c9a',lambda m:m.group(1)+display,text,count=1)
        if count:
            payload['stage/index.html']=text.encode('utf-8')
            title_transform={'source_sha256':digest(original),'new_sha256':digest(payload['stage/index.html']),
                             'scope':'one existing browser title label only; no audio metadata relabel'}
    for name in ('ui/ui_layout_spec.json','ui/ui_tokens.json','ui/board_touch_layout.json','config/board_ui_services.json',
                 'common/schemas/board_ui_snapshot.schema.json','common/schemas/board_ui_command.schema.json','common/schemas/board_ui_ack.schema.json',
                 'config/pan_manual.local.json','config/pan_face.local.json','config/pan_direction.current.json'):
        source=join(baseline['runtime']+'/aura',name)
        payload['runtime/aura/'+name]=files.read(source,262144)
        need(digest(payload['runtime/aura/'+name])==baseline['pins'][name],'fresh_public_ui_resource_changed')
    need('runtime/aura/'+gui['font_file'] in payload,'fresh_public_font_missing')
    for row in policy['models']:
        need(files.info(row['path'],canonical=True)['bytes']==row['bytes']
             and files.hash(row['path'])==row['sha256'],'same_model_cached_resource_changed')
    dependencies=[dependency(row,files) for row in policy['dependencies']]
    model_dir=policy['speaker_directory'];speaker_manifest=parse(files.read(model_dir+'/manifest.json',65536,canonical=True))
    need(files.hash(model_dir+'/manifest.json')==policy['speaker_manifest_sha256']
         and speaker_manifest.get('dimension')==192 and speaker_manifest.get('sample_rate')==16000
         and speaker_manifest.get('precision')=='float32' and isinstance(speaker_manifest.get('source_model_id'),str),
         'original_ecapa_descriptor_required')
    face=policy['face_readback'];face_raw=files.read(face['path'],65536,canonical=True)
    need(digest(face_raw)==face['sha256'],'fresh_private_readback_metadata_changed')
    face_meta=parse(face_raw)
    need(face_meta.get('board_boot_id')==policy['camera']['boot']
         and face_meta.get('camera_pid')==policy['camera']['pid']
         and face_meta.get('camera_start_ticks')==policy['camera']['birth'],'private_readback_owner_binding_changed')
    payload.update(feedback(files,policy['feedback'],target))
    fragment=parse(payload['runtime/yuki_business.config.fragment.json']);config=dict(gui,**fragment)
    config.update(audio_frontend=None,early_listen=False)
    missing=[]
    if (not isinstance(utc_bounds,(tuple,list)) or len(utc_bounds)!=2
            or any(type(n) not in (int,float) or not math.isfinite(n) for n in utc_bounds)
            or not 1704067200<=utc_bounds[0]<utc_bounds[1] or utc_bounds[1]-utc_bounds[0]>604800):
        missing.append('board_business.utc_bounds (explicit trusted Windows UTC, never board wall clock)')
    config['board_business']={'enabled':True,'private_root':target+'/private/business',
        'utc_bounds':list(utc_bounds) if not missing else None,'data_origin':'synthetic',
        'asr_directory':policy['asr_directory'],'frontend_directory':policy['frontend_directory'],
        'feedback_manifest':target+'/runtime/public_cues/feedback.json','model_port':8797,
        'timeout_ms':120000,'timezone':'America/Los_Angeles','entry_mode':'voice_first',
        'asr_threads':2,'frontend_threads':1,'visual_device_id':'board-camera',
        'speaker':{'enabled':True,'model_directory':model_dir,'manifest_sha256':policy['speaker_manifest_sha256'],
                   'expected_model_id':speaker_manifest['source_model_id'],'anonymous_config':{'enabled':True}},
        'face_readback':copy.deepcopy(face)}
    need(config['portrait_offload']=={'enabled':False} and config['native_avatar'] is True
         and config['stable_avatar_fps']==16 and config['persistent_audio'] is True
         and config['streaming_conversation'] is True and config['handsfree_dialogue'] is True,
         'paired_board_factory_configuration_required')
    payload['runtime/aura/config/board_avatar_gtk.json']=encoded(config)
    payload['runtime/avatar_service_settings.json']=encoded({'schema_version':'aura-ui-1','connection':{'enabled':True,'host':'127.0.0.1','port':8790}})
    payload['private/ui_settings.json']=encoded({'schema_version':1,'values':{'volume':70,'muted':False,'fullscreen':True,'economy':False}})
    # The byte-exact original pan wrapper is retained for matched FAULT/null
    # monitoring/control costs. Its child validates the new own startup pins.
    # No source/threshold/boot/FDT/release path is changed in these JSON files.
    for name in ('pan_manual.local.json','pan_face.local.json','pan_direction.current.json'):
        value=parse(payload['runtime/aura/config/'+name])
        def no_credential(node):
            if isinstance(node,dict):
                for key,item in node.items():
                    need(not re.search(r'(?:password|secret|credential|private_key|access_token|auth_token|control_key)',key,re.I),
                         'protected_pan_metadata_contains_credential_field')
                    no_credential(item)
            elif isinstance(node,list):
                for item in node:no_credential(item)
        no_credential(value)
    startup_config=copy.deepcopy(startup)
    need(digest(payload['runtime/aura/tools/board_avatar_pan.py'])==startup['gui_sha256']
         ==baseline['pins']['tools/board_avatar_pan.py'],'same_original_pan_entry_required')
    startup_config['runtime']=target+'/runtime'
    startup_config['gui_sha256']=digest(payload['runtime/aura/tools/board_avatar_pan.py'])
    startup_config['component_sha256']={name[len('runtime/aura/'):]:digest(raw) for name,raw in payload.items()
                                       if name.startswith('runtime/aura/')}
    payload['startup/config.json']=encoded(startup_config)
    # Defaults are constructed in new runtime; no old settings/key/selection
    # file is copied. The paired monitor starts RAM-false in frozen source.
    deps=[row['root'] for row in policy['dependencies'] if row['kind']!='numpy']
    environment={'DISPLAY':startup['display'],'HOME':target+'/private/home',
        'XDG_CACHE_HOME':target+'/private/cache','XDG_DATA_HOME':target+'/private/data','TMPDIR':target+'/private/tmp',
        'PYTHONPATH':':'.join([target+'/runtime/aura']+deps),'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1',
        'PYTHONPYCACHEPREFIX':target+'/private/pycache','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    launch={'schema':'aura-yuki-synthetic-launch-stencil-1','root_only':True,'automatic_start':False,
        'command':['/usr/bin/python3','-B',target+'/runtime/aura/tools/board_avatar_pan.py','--root',target+'/stage',
                   '--config',target+'/runtime/aura/config/board_avatar_gtk.json','--settings-file',target+'/private/ui_settings.json',
                   '--evidence-root',target+'/evidence/gui-capacity-1'],
        'environment':environment,'inherit_only_if_already_authorized':['XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS'],
        'single_publisher_lock':startup['lock_file'],'original_service':startup['service_name'],
        'microphone_initially_enabled':False,'following_initially_enabled':False,
        'pan_wrapper_and_fault_monitor':'same original byte-exact board_avatar_pan.py and protected JSON; no binding relaxation',
        'service_swap_control':'parent root only; no start/stop command generated here'}
    payload['launch.json']=encoded(launch)
    resources={'models':policy['models'],'dependencies':dependencies,'face_readback':face,
               'read_only_references':True,'bytecode_writes_redirected_or_disabled':True}
    payload['resource_refs.json']=encoded(resources)
    mapping={name:{'bytes':len(raw),'sha256':digest(raw)} for name,raw in sorted(payload.items())}
    changes={k:{'baseline':v,'candidate':mapping.get('runtime/aura/'+k,{}).get('sha256')}
             for k,v in baseline['pins'].items() if mapping.get('runtime/aura/'+k,{}).get('sha256')!=v}
    plan={'schema':'aura-yuki-synthetic-assembly-1','ready':not missing,'missing_runtime_fields':missing,
          'target':target,'source':policy['source'],'baseline_startup_sha256':baseline['startup_sha256'],
          'baseline_component_pins':baseline['pins'],'baseline_observations':sources,'candidate_files':mapping,
          'component_changes_or_omissions':changes,'dependencies':dependencies,'models':policy['models'],
          'public_browser_title_transform':title_transform,
          'data_origin':'synthetic','business_state_copied':False,'old_png_assets_copied':False,
          'private_keys_or_databases_copied':False,'original_files_modified':False,'launch':launch,
          'runtime_publish_gates':['Root serial single-publisher service handoff','Fresh face readback owner preflight',
              'Original mechanical FAULT/null and no following; no pan/follow command in this capacity trial',
              'Actual X11/EGL first swap readiness','Actual public audio/ASR/PCM ACK/cancel/queue16fps capacity',
              'New paired demo greeting cache is not supplied; do not use old self-introduction'],
          'inspector_imported_gui_audio_or_model':False}
    plan['inspection_sha256']=digest(encoded(plan))
    return plan,payload


def stage(plan,payload,expected,files=None):
    files=files or Files();need(os.name=='posix' and os.geteuid()==0,'actual_root_posix_stage_required')
    need(plan['ready'] and plan['inspection_sha256']==expected,'reviewed_ready_inspection_required')
    root=plan['target'];files.create_root(root)
    for directory in ('runtime','stage/cache','private/business','private/home','private/cache','private/data','private/tmp','private/pycache','evidence'):
        files.directory(join(root,directory))
    for name,raw in sorted(payload.items()):files.write(join(root,name),raw)
    files.write(root+'/assembly_manifest.json',encoded(plan))
    for name,row in plan['candidate_files'].items():
        need(files.hash(join(root,name))==row['sha256'],'new_staged_file_verification_failed')
    return {'status':'SYNTHETIC_RUNTIME_STAGED_NOT_STARTED','target':root,'inspection_sha256':expected,
            'files':len(payload),'source_components':plan['source']['python_files'],
            'data_origin':'synthetic','gui_started':False,'service_action_sent':False,'original_files_modified':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['inspect','stage'],nargs='?',default='inspect')
    parser.add_argument('--policy',required=True);parser.add_argument('--policy-sha256',required=True)
    parser.add_argument('--archive',required=True);parser.add_argument('--target',required=True)
    parser.add_argument('--utc-start',type=float);parser.add_argument('--utc-end',type=float)
    parser.add_argument('--expected-inspection-sha256');args=parser.parse_args()
    try:
        files=Files();raw=files.read(args.policy,262144,canonical=True)
        need(sha(args.policy_sha256) and digest(raw)==args.policy_sha256,'reviewed_policy_sha_required')
        policy=parse(raw);bounds=None if args.utc_start is None or args.utc_end is None else [args.utc_start,args.utc_end]
        plan,payload=inspect(policy,args.archive,args.target,bounds,files=files)
        if args.action=='stage':
            need(args.expected_inspection_sha256,'stage_requires_reviewed_inspection')
            # Repeat all current source/resource checks before creating any
            # directory. This tool never starts a source or imports a model.
            again,second=inspect(policy,args.archive,args.target,bounds,files=files)
            need(again==plan and second==payload,'inspection_changed_before_stage')
            result=stage(plan,payload,args.expected_inspection_sha256,files)
        else:
            result={'status':'READY_FOR_REVIEW' if plan['ready'] else 'MISSING_RUNTIME_FIELDS',
                    'ready':plan['ready'],'inspection_sha256':plan['inspection_sha256'],
                    'target':args.target,'candidate_files':len(payload),'missing_runtime_fields':plan['missing_runtime_fields'],
                    'model_files':len(policy['models']),'dependency_roots':len(plan['dependencies']),
                    'baseline_pins':len(policy['baseline']['pins']),'writes_performed':False,
                    'service_or_model_calls':False,'data_origin':'synthetic'}
    except Exception as exc:
        result={'status':'REFUSED','reason':str(exc) if isinstance(exc,Refused) else type(exc).__name__,
                'gui_started':False,'service_action_sent':False,'original_files_modified':False}
    print(json.dumps(result,ensure_ascii=True,sort_keys=True))
    return 2 if result['status'] in ('REFUSED','MISSING_RUNTIME_FIELDS') else 0


if __name__=='__main__':raise SystemExit(main())
