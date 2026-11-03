"""Prepare pause/resume source and exact rollback only after a real passing public ARM receipt."""
from pathlib import Path
import argparse,ast,base64,copy,difflib,hashlib,json

HERE=Path(__file__).resolve().parents[1];PROJECT=HERE.parents[3]
JOINT=HERE.parent/'joint_performance_20261101'
BASE=JOINT/'package/subtitle_receipt';OUT=HERE/'package/pause_resume'
PUBLIC=PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/joint_balance_20261101/continued_validation_20261101/pause_resume_candidate'
SOURCE='tools/voice_first_recording.py';ROOT='/home/root/aura-board-business-20261030/production-5259eab11e42af13'
STAGE='/home/root/aura-board-business-20261030/control-production-v1/pause-resume-current-54fa17ac97e3fdbe'
def encoded(v):return (json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def sha(v):return hashlib.sha256(v).hexdigest()
def read(p):return json.loads(p.read_bytes())
def put(name,data):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(data)
def save(name,v):put(name,encoded(v))

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--arm-evidence',type=Path,required=True);args=parser.parse_args()
 assert not OUT.exists()
 arm=read(args.arm_evidence);assert arm['result']['status']=='PASSED'
 assert arm['result']['machine']=='aarch64' and arm['result']['public_tests']==9
 assert arm['result']['private_database_or_device_services_used'] is False
 assert arm['result']['candidate_sha256']=='54fa17ac97e3fdbeeb2725b6534a86dec9ece60839f2b14ffa77c348e714dafc'
 m=read(BASE/'BUNDLE_MANIFEST.json')
 for name,pin in m['files'].items():assert sha((BASE/name).read_bytes())==pin
 old_spec_raw=(BASE/'candidate_spec.json').read_bytes();old_spec=json.loads(old_spec_raw)
 assert sha(old_spec_raw)=='62b99e24560229c78a3be000fed5752b6a50c4fb16ab6bc2c88e987561831177'
 assert old_spec_raw==(PROJECT/'deliverables/2026-10-30_board_owner/integration/production_business_acceptance/spec.json').read_bytes()
 old_start_raw=(BASE/'candidate_startup.json').read_bytes();old_manifest_raw=(BASE/'candidate_manifest.json').read_bytes()
 assert sha(old_start_raw)==old_spec['startup_sha256']=='22317f7933447b28a2ca535a47246de8b3869989cc0d964a13cd169cd2289311'
 assert sha(old_manifest_raw)==old_spec['source_manifest_sha256']=='5b741bff8039a4f71110b06cce88ff40bea32a27ace718a263f6879f79deaa2b'
 old_source=(PUBLIC/'before'/SOURCE).read_bytes();new_source=(PUBLIC/'after'/SOURCE).read_bytes()
 assert sha(old_source)==old_spec['component_sha256'][SOURCE]=='57375530fddbcf7a8f431201bf86ba904d289828e69a82cdee81ab0324987427'
 assert sha(new_source)==arm['result']['candidate_sha256'];ast.parse(new_source.decode())
 startup=json.loads(old_start_raw);startup['component_sha256'][SOURCE]=sha(new_source);sraw=encoded(startup)
 manifest=json.loads(old_manifest_raw);manifest['component_pins'][SOURCE]=sha(new_source)
 manifest['files']['runtime/aura/'+SOURCE]=dict(bytes=len(new_source),sha256=sha(new_source))
 manifest['files']['startup/config.json']=dict(bytes=len(sraw),sha256=sha(sraw))
 revision=dict(stage=STAGE,source=SOURCE,before_sha256=sha(old_source),after_sha256=sha(new_source),
               parent_spec_sha256=sha(old_spec_raw),parent_startup_sha256=sha(old_start_raw),parent_manifest_sha256=sha(old_manifest_raw),
               arm_evidence_sha256=sha(args.arm_evidence.read_bytes()),subtitle_and_single_projection_retained=True,unchanged_components=379)
 manifest['pause_resume_current_conversation']=revision;mraw=encoded(manifest)
 spec=copy.deepcopy(old_spec);spec['component_sha256'][SOURCE]=sha(new_source);spec['release_sources'][SOURCE]=sha(new_source)
 spec.update(startup_sha256=sha(sraw),source_manifest_sha256=sha(mraw),pause_resume_current_conversation=dict(revision,state='APPLIED'));nraw=encoded(spec)
 assert len(spec['component_sha256'])==380 and [p for p in spec['component_sha256'] if spec['component_sha256'][p]!=old_spec['component_sha256'][p]]==[SOURCE]
 assert spec['configuration_sha256']==old_spec['configuration_sha256']
 for key in old_spec:
  if key in ('startup_sha256','source_manifest_sha256','component_sha256','release_sources'):continue
  assert spec[key]==old_spec[key]
 parents=copy.deepcopy(read(BASE/'forward_plan.json')['parent_transactions'])
 parents['subtitle_submit_receipt']=dict(stage=old_spec['subtitle_submit_receipt']['stage'],field='applied_spec_sha256',spec_sha256=sha(old_spec_raw))
 current=read(HERE/'evidence/preflight_1793539648715521000.json')['result']
 assert current['can_continue_plan_preparation'] is True
 current=dict(current,owners={role:{key:row[key] for key in ('pid','birth_ticks','command_sha256')} for role,row in current['owners_discovered_fresh'].items()})
 assert current['state']['listening_state']=='PAUSED' and current['state']['following'] is False
 for name,data in [('base_spec.json',old_spec_raw),('candidate_spec.json',nraw),('base_startup.json',old_start_raw),
                   ('candidate_startup.json',sraw),('base_manifest.json',old_manifest_raw),('candidate_manifest.json',mraw),
                   ('gui.json',(BASE/'gui.json').read_bytes()),('rollback/voice_first_recording.py',old_source),
                   ('payload/voice_first_recording.py',new_source),('publisher_definitions.py',(BASE/'publisher_definitions.py').read_bytes()),
                   ('camera_binding_runtime.py',(BASE/'camera_binding_runtime.py').read_bytes()),
                   ('single_projection_overlay.py',(BASE/'single_projection_overlay.py').read_bytes())]:put(name,data)
 targets=[('voice_first_recording.py',ROOT+'/runtime/aura/'+SOURCE,old_source,new_source),
          ('production-source-manifest.json',ROOT+'/production_source_manifest.json',old_manifest_raw,mraw),
          ('startup-config.json',ROOT+'/startup/config.json',old_start_raw,sraw)]
 for direction in ('forward','rollback'):
  rollback=direction=='rollback';stage=STAGE+('-rollback' if rollback else '')
  before_spec=spec if rollback else old_spec;after_spec=old_spec if rollback else spec
  rows={name:dict(path=path,old_sha256=sha(new if rollback else old),new_sha256=sha(old if rollback else new),
                  new_base64=base64.b64encode(old if rollback else new).decode()) for name,path,old,new in targets}
  tx=dict(schema='aura-pause-resume-current-transaction-1',direction=direction,stage=stage,
          parent_spec_sha256=sha(encoded(before_spec)),applied_spec_sha256=sha(encoded(after_spec)),
          targets={k:{x:y for x,y in v.items() if x!='new_base64'} for k,v in rows.items()})
  plan=dict(stage=stage,marker='pause_resume_current_conversation'+('_rollback' if rollback else ''),direction=direction,
            changed_source=SOURCE,targets=rows,transaction=tx,transaction_sha256=sha(encoded(tx)),
            expected_before_owners=current['owners'],face_readback=spec['face_readback'],parent_transactions=copy.deepcopy(parents),
            allow_known_mixed_on_first_apply=rollback)
  if rollback:plan['parent_transactions']['pause_resume_current_conversation']=dict(stage=STAGE,field='applied_spec_sha256',spec_sha256=sha(nraw),allowed_states=['INTENT','APPLIED'])
  save(direction+'_plan.json',plan)
 runner=(JOINT/'tools/publish_subtitle_receipt.py').read_text('utf-8')
 for old,new in [("root=HERE/'package/subtitle_receipt'","root=HERE/'package/pause_resume'"),
                 ("review['candidate_source_sha256']=='de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2'", "review['candidate_source_sha256']=='54fa17ac97e3fdbeeb2725b6534a86dec9ece60839f2b14ffa77c348e714dafc'"),
                 ("('subtitle_receipt_'+a.direction", "('pause_resume_'+a.direction")]:
  assert runner.count(old)==1;runner=runner.replace(old,new,1)
 ast.parse(runner);runner_path=HERE/'tools/publish_pause_resume.py'
 with runner_path.open('x',encoding='utf-8',newline='\n') as f:f.write(runner)
 put('source.patch',''.join(difflib.unified_diff(old_source.decode().splitlines(True),new_source.decode().splitlines(True),fromfile='before/'+SOURCE,tofile='after/'+SOURCE)).encode())
 report=dict(schema='aura-pause-resume-current-publication-preparation-1',status='PREPARED_FOR_LOCAL_REVIEW_NOT_APPLIED',
             old_spec_sha256=sha(old_spec_raw),new_spec_sha256=sha(nraw),new_startup_sha256=sha(sraw),new_manifest_sha256=sha(mraw),
             source_before_sha256=sha(old_source),source_after_sha256=sha(new_source),changed_source=SOURCE,unchanged_components=379,
             configuration_sha256=spec['configuration_sha256'],camera_and_wide_firmware_unchanged=True,
             original_25_controller_and_all_pan_configurations_unchanged=True,source_scope='Explicit continue retains the same current anonymous conversation; original selector and grant guards retained',
             arm_evidence=str(args.arm_evidence),arm_evidence_sha256=sha(args.arm_evidence.read_bytes()),
             publisher=str(runner_path),publisher_sha256=sha(runner_path.read_bytes()),
             forward_stage=STAGE,rollback_stage=STAGE+'-rollback',normal_WM_DELETE_only=True,production_modified=False)
 save('PREPARATION.json',report)
 files={p.relative_to(OUT).as_posix():sha(p.read_bytes()) for p in OUT.rglob('*') if p.is_file()}
 files['../../tools/publish_pause_resume.py']=sha(runner_path.read_bytes())
 save('BUNDLE_MANIFEST.json',dict(schema='aura-pause-resume-current-publisher-bundle-1',status='PREPARED_NOT_APPLIED',files=files,
                                source=SOURCE,source_sha256=sha(new_source),new_spec_sha256=sha(nraw),new_startup_sha256=sha(sraw),new_manifest_sha256=sha(mraw)))
 print(json.dumps(dict(bundle=str(OUT),bundle_manifest_sha256=sha((OUT/'BUNDLE_MANIFEST.json').read_bytes()),**report)))

if __name__=='__main__':main()
