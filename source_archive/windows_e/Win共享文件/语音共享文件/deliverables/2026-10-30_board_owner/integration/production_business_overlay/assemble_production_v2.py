"""Root-only source assembler. Default inspect never starts/open stores/models.

Only explicitly pinned public source/assets are copied. No unit, GUI, database,
cache, HOME or settings mutation. Root separately migrates data and publishes.
"""
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import zipfile

BASE='/home/root/aura-character-xuefei-20261030/f94fca2c94288acb'
STARTUP='4c78824ba9c1c04bb95389a49b64215a7f624a323becae637bc8d4e7c4db4d7e'
LIBRARY='887546c09eb1897845c8d7f55a9e3f9b9c761448c7410f2b599259ae0b51efd2'
PREFIX='/home/root/aura-board-business-20261030/'
LAUNCHER='5b15a8cf1813935679e5f4d30eb788e9c8d6ae18826669009d06c92cba152e03'


def need(value,code):
    if not value:raise ValueError(code)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def parse(raw):
    def unique(pairs):
        result={}
        for k,v in pairs:need(k not in result,'duplicate_json_key');result[k]=v
        return result
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite_json')))
def relative(name):
    p=PurePosixPath(name);need(isinstance(name,str) and name and str(p)==name and not p.is_absolute()
        and '..' not in p.parts and '\\' not in name,'unsafe_source_relative_path');return name
def read(path,expected=None,maximum=33554432):
    path=Path(path);need(path.is_absolute() and path.resolve(strict=True)==path and not path.is_symlink()
        and path.is_file() and path.stat().st_size<=maximum,'canonical_bounded_public_file_required')
    raw=path.read_bytes();need(len(raw)<=maximum and (expected is None or sha(raw)==expected),'public_file_changed');return raw
def source_name(name):
    relative(name);need(name.startswith('aura/') and not any(x in PurePosixPath(name).parts for x in
        ('cache','managed-runs','venv','.venv','__pycache__')) and Path(name).suffix.lower() not in
        ('.db','.sqlite','.sqlite3','.key','.pem','.gguf','.bin','.onnx','.wav','.pcm','.log'), 'source_asset_only')
    return name
def overlay(archive,manifest):
    raw=read(archive,manifest['overlay_sha256']);result={};total=0
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        rows=z.infolist();need(len(rows)==len(manifest['overlay_files']) and len({v.filename for v in rows})==len(rows),'overlay_members_changed')
        for row in rows:
            name=source_name(row.filename);total+=row.file_size
            need(not row.is_dir() and not stat.S_ISLNK(row.external_attr>>16) and row.file_size<=16777216 and total<=33554432,'bounded_plain_overlay_required')
            data=z.read(row);need(sha(data)==manifest['overlay_files'][name]['sha256'],'overlay_source_changed')
            result[name]=data
    return result


def assemble(args):
    manifest=parse(read(args.manifest,args.manifest_sha256));need(manifest['basis_startup_sha256']==STARTUP,'reviewed_current_basis_required')
    old=parse(read(BASE+'/startup/config.json',STARTUP));need(old['runtime']==BASE+'/runtime' and len(old['component_sha256'])==304,'current304_basis_required')
    payload={}
    for name,expected in old['component_sha256'].items():
        relative(name);payload['aura/'+name]=read(BASE+'/runtime/aura/'+name,expected)
    need(sha(payload['aura/tools/libaura_yuki.so'])==LIBRARY,'waist_framing_native_must_be_preserved')
    payload.update(overlay(args.overlay,manifest))
    need(set(payload)==set(manifest['files']) and all(sha(raw)==manifest['files'][name]['sha256'] for name,raw in payload.items()),'complete_source_closure_changed')
    if args.extra_sources:
        # Optional root-pinned migration module closure; never data snapshots.
        need(isinstance(args.extra_sources_sha256,str) and re.fullmatch('[0-9a-f]{64}',args.extra_sources_sha256),
             'explicit_extra_source_manifest_fingerprint_required')
        extra=parse(read(args.extra_sources,args.extra_sources_sha256))
        need(extra.get('schema')=='aura.production-source-dependencies.v1','extra_source_map_schema')
        for name,row in extra['files'].items():payload[source_name(name)]=read(row['path'],row['sha256'])
    need(sha(payload['aura/tools/libaura_yuki.so'])==LIBRARY,'dependency_map_cannot_replace_waist_native')
    for name,raw in payload.items():
        if name.endswith('.py'):ast.parse(raw,feature_version=(3,9))
    config=parse(payload['aura/config/board_avatar_gtk.json']);overrides=parse(read(args.config,args.config_sha256,262144))
    need(isinstance(overrides,dict) and set(overrides)<= {'board_business','profile_access'} and 'board_business' in overrides,'explicit_production_configuration_required')
    business=overrides['board_business'];need(business.get('enabled') is True and business.get('data_origin')=='board'
        and business.get('private_root')=='/home/root/.local/share/aura-board-business','migrated_private_board_storage_required')
    need(type(business.get('retention_enabled',False)) is bool and (not business.get('retention_enabled',False) or args.allow_retention), 'retention_disabled_until_explicit_approved_restart')
    need(business.get('feedback_manifest')==config['formal_static_cues']['path'] and
         business.get('feedback_manifest_sha256')==config['formal_static_cues']['sha256'],'selected_public_cue_binding_required')
    need(business.get('model_port',8797)==8797 and business.get('asr_threads',2)==2 and business.get('frontend_threads',1)==1,
         'original_models_and_thread_configuration_required')
    need(type(business.get('resume_saved_conversation',True)) is bool,'explicit_saved_conversation_policy_required')
    config.update(board_business=business,audio_frontend=None,early_listen=False)
    payload['aura/config/board_avatar_gtk.json']=encoded(config)
    if 'profile_access' in overrides:
        profile=overrides['profile_access'];need(isinstance(profile,dict) and set(profile) in
            ({'control_key_file'},{'control_key_file','control_key_sha256'}) and Path(profile['control_key_file']).is_absolute(),
            'private_board_profile_credential_reference_only')
        payload['aura/config/profile_access.local.json']=encoded(profile)  # Only a path/verifier, never key bytes.
    public_voice={
        'selection.json':'c3d699f6611fa808e468c1a7dcba6953a85e375cfdcac3d9349ecb52ae5f42ce',
        'base_model_verification.json':'cffc0df49ff2d7d42c57f6d4140f3b758ce138628eca9d87490d666a02da723e',
        'reference/soft_young.wav':'0d252fc92cfd0002f61d05f107b816d092fd5086a281e98e94d3cdc5ccf66604'}
    runtime={'runtime/'+name:raw for name,raw in payload.items()}
    for name,expected in public_voice.items():
        voice_relative='deliverables/2026-10-06_voice_selected_soft_young/'+name
        runtime['runtime/'+voice_relative]=read(BASE+'/runtime/'+voice_relative,expected)
    need(args.target.startswith(PREFIX) and '..' not in PurePosixPath(args.target).parts
         and len(PurePosixPath(args.target).parts)==len(PurePosixPath(PREFIX).parts)+1,'new_business_source_namespace_required')
    new=dict(old,runtime=args.target+'/runtime',component_sha256={name[5:]:sha(raw) for name,raw in payload.items()})
    new['gui_sha256']=new['component_sha256']['tools/board_avatar_pan.py']
    runtime['startup/config.json']=encoded(new)
    runtime['startup/launcher.py']=read(BASE+'/startup/launcher.py',LAUNCHER)
    plan=dict(schema='aura.production-runtime-assembly.v1',target=args.target,basis_startup_sha256=STARTUP,
        source_manifest_sha256=args.manifest_sha256,configuration_sha256=args.config_sha256,
        extra_sources_sha256=args.extra_sources_sha256,
        files={name:{'sha256':sha(raw),'bytes':len(raw)} for name,raw in sorted(runtime.items())},
        component_pins=new['component_sha256'],native_library_sha256=LIBRARY,
        stage_or_home_settings_or_databases_copied=False,unit_or_gui_action=False,
        retention_enabled=business.get('retention_enabled',False),production_store_opened=False)
    return plan,runtime


def stage(plan,payload):
    root=Path(plan['target']);need(not root.exists(),'new_target_only_no_overwrite')
    root.mkdir(mode=0o700,parents=True);need(root.resolve(strict=True)==root,'canonical_new_root_required')
    for name,raw in payload.items():
        path=root/name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    (root/'production_source_manifest.json').write_bytes(encoded(plan));(root/'production_source_manifest.json').chmod(0o600)
    for name,row in plan['files'].items():read(root/name,row['sha256'])
    return dict(status='PRODUCTION_SOURCE_STAGED_NOT_STARTED',target=str(root),component_pins=len(plan['component_pins']),
                startup_sha256=plan['files']['startup/config.json']['sha256'],retention_enabled=plan['retention_enabled'],
                no_real_store_opened=True,no_unit_or_gui_action=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action',nargs='?',default='inspect',choices=('inspect','stage','startup-check'))
    for name in ('manifest','manifest-sha256','overlay','config','config-sha256','target'):ap.add_argument('--'+name,required=True)
    ap.add_argument('--extra-sources');ap.add_argument('--extra-sources-sha256');ap.add_argument('--allow-retention',action='store_true')
    args=ap.parse_args()
    try:
        need(os.name=='posix' and os.geteuid()==0,'root_board_source_assembly_only')
        if args.action=='startup-check':
            need(args.target.startswith(PREFIX) and '..' not in PurePosixPath(args.target).parts
                 and Path(args.target).resolve(strict=True)==Path(args.target),'reviewed_namespace_required')
            read(args.target+'/startup/launcher.py',LAUNCHER)
            startup=parse(read(args.target+'/startup/config.json'))
            need(startup['runtime']==args.target+'/runtime','staged_runtime_rebase_changed')
            for relative_path,expected in startup['component_sha256'].items():
                read(args.target+'/runtime/aura/'+relative(relative_path),expected)
            env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin',PYTHONDONTWRITEBYTECODE='1')
            r=subprocess.run(['/usr/bin/python3','-B',args.target+'/startup/launcher.py','--config',
                args.target+'/startup/config.json','--preflight'],capture_output=True,text=True,timeout=25,env=env)
            need(r.returncode==0 and len(r.stdout)<=65536,'original_launcher_source_preflight_failed')
            result=dict(status='SOURCE_STARTUP_PREFLIGHT_ONLY',output=r.stdout,models_or_gui_or_store_started=False)
        else:
            plan,payload=assemble(args)
            result=stage(plan,payload) if args.action=='stage' else dict(status='SOURCE_INSPECTED_ONLY',target=args.target,
                files=len(payload),component_pins=len(plan['component_pins']),plan_sha256=sha(encoded(plan)),
                retention_enabled=plan['retention_enabled'],models_or_gui_or_store_started=False)
        print(json.dumps(result));return 0
    except Exception as exc:
        print(json.dumps(dict(status='REFUSED_NO_SERVICE_OR_STORE_ACTION',error_type=type(exc).__name__,
                              error_code=str(exc) if isinstance(exc,ValueError) else 'source_preflight_failed')));return 2
if __name__=='__main__':raise SystemExit(main())
