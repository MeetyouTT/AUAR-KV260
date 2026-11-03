"""Prepare the reviewed subtitle source and exact rollback after a passing public ARM receipt."""
from pathlib import Path
import argparse,ast,base64,copy,difflib,hashlib,json

HERE=Path(__file__).resolve().parents[1];PROJECT=HERE.parents[3]
BASE=HERE/'package/single_projection';OUT=HERE/'package/subtitle_receipt'
PUBLIC=PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/joint_balance_20261101/subtitle_repair'
SOURCE='tools/production_memory_presentation.py';ROOT='/home/root/aura-board-business-20261030/production-5259eab11e42af13'
STAGE='/home/root/aura-board-business-20261030/control-production-v1/subtitle-submit-receipt-de04c6cd22e3672f'
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
 assert arm['result']['candidate_sha256']=='de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2'
 m=read(BASE/'BUNDLE_MANIFEST.json')
 for name,pin in m['files'].items():assert sha((BASE/name).read_bytes())==pin
 old_spec_raw=(BASE/'candidate_spec.json').read_bytes();old_spec=json.loads(old_spec_raw)
 assert sha(old_spec_raw)=='05e9035981fc2771010d92dd046b0af041a9c618e6c0260626aa34380b420d4d'
 assert old_spec_raw==(PROJECT/'deliverables/2026-10-30_board_owner/integration/production_business_acceptance/spec.json').read_bytes()
 old_start_raw=(BASE/'candidate_startup.json').read_bytes();old_manifest_raw=(BASE/'candidate_manifest.json').read_bytes()
 assert sha(old_start_raw)==old_spec['startup_sha256']=='71c28c2d4a15585a0370790c9be62ab5c1d975d0ac70626613429d355e83bb87'
 assert sha(old_manifest_raw)==old_spec['source_manifest_sha256']=='e35ec0e32bb5b4d5c17ce11396753bcb36ad13eb651c9d1c3f57d1d745786020'
 old_source=(PUBLIC/'before'/SOURCE).read_bytes();new_source=(PUBLIC/'after'/SOURCE).read_bytes()
 assert sha(old_source)==old_spec['component_sha256'][SOURCE]=='984d3ca24067bf5129e9ce3b0054f32cced717b6b8824eab347476bef2f9e502'
 assert sha(new_source)==arm['result']['candidate_sha256'];ast.parse(new_source.decode())
 startup=json.loads(old_start_raw);startup['component_sha256'][SOURCE]=sha(new_source);sraw=encoded(startup)
 manifest=json.loads(old_manifest_raw);manifest['component_pins'][SOURCE]=sha(new_source)
 manifest['files']['runtime/aura/'+SOURCE]=dict(bytes=len(new_source),sha256=sha(new_source))
 manifest['files']['startup/config.json']=dict(bytes=len(sraw),sha256=sha(sraw))
 revision=dict(stage=STAGE,source=SOURCE,before_sha256=sha(old_source),after_sha256=sha(new_source),
               parent_spec_sha256=sha(old_spec_raw),parent_startup_sha256=sha(old_start_raw),parent_manifest_sha256=sha(old_manifest_raw),
               arm_evidence_sha256=sha(args.arm_evidence.read_bytes()),single_metadata_projection_retained=True,unchanged_components=379)
 manifest['subtitle_submit_receipt']=revision;mraw=encoded(manifest)
 spec=copy.deepcopy(old_spec);spec['component_sha256'][SOURCE]=sha(new_source);spec['release_sources'][SOURCE]=sha(new_source)
 spec.update(startup_sha256=sha(sraw),source_manifest_sha256=sha(mraw),subtitle_submit_receipt=dict(revision,state='APPLIED'));nraw=encoded(spec)
 assert len(spec['component_sha256'])==380 and [p for p in spec['component_sha256'] if spec['component_sha256'][p]!=old_spec['component_sha256'][p]]==[SOURCE]
 assert spec['configuration_sha256']==old_spec['configuration_sha256']
 for key in ('camera_owner','face_readback','axis_original_rebind','axis_direction_rebind','single_metadata_projection','summary_followup'):
  assert spec[key]==old_spec[key]
 parents=copy.deepcopy(read(BASE/'forward_plan.json')['parent_transactions'])
 parents['single_metadata_projection']=dict(stage=old_spec['single_metadata_projection']['stage'],field='applied_spec_sha256',spec_sha256=sha(old_spec_raw))
 current=read(HERE/'evidence/live_trial_1793535383341989300/FINAL_PAUSED.json')['proof']
 assert current['state']['listening_state']=='PAUSED' and current['state']['following'] is False
 for name,data in [('base_spec.json',old_spec_raw),('candidate_spec.json',nraw),('base_startup.json',old_start_raw),
                   ('candidate_startup.json',sraw),('base_manifest.json',old_manifest_raw),('candidate_manifest.json',mraw),
                   ('gui.json',(BASE/'gui.json').read_bytes()),('rollback/production_memory_presentation.py',old_source),
                   ('payload/production_memory_presentation.py',new_source),('publisher_definitions.py',(BASE/'publisher_definitions.py').read_bytes()),
                   ('camera_binding_runtime.py',(BASE/'camera_binding_runtime.py').read_bytes()),
                   ('single_projection_overlay.py',(BASE/'single_projection_overlay.py').read_bytes())]:put(name,data)
 targets=[('production_memory_presentation.py',ROOT+'/runtime/aura/'+SOURCE,old_source,new_source),
          ('production-source-manifest.json',ROOT+'/production_source_manifest.json',old_manifest_raw,mraw),
          ('startup-config.json',ROOT+'/startup/config.json',old_start_raw,sraw)]
 for direction in ('forward','rollback'):
  rollback=direction=='rollback';stage=STAGE+('-rollback' if rollback else '')
  before_spec=spec if rollback else old_spec;after_spec=old_spec if rollback else spec
  rows={name:dict(path=path,old_sha256=sha(new if rollback else old),new_sha256=sha(old if rollback else new),
                  new_base64=base64.b64encode(old if rollback else new).decode()) for name,path,old,new in targets}
  tx=dict(schema='aura-subtitle-submit-receipt-transaction-1',direction=direction,stage=stage,
          parent_spec_sha256=sha(encoded(before_spec)),applied_spec_sha256=sha(encoded(after_spec)),
          targets={k:{x:y for x,y in v.items() if x!='new_base64'} for k,v in rows.items()})
  plan=dict(stage=stage,marker='subtitle_submit_receipt'+('_rollback' if rollback else ''),direction=direction,
            changed_source=SOURCE,targets=rows,transaction=tx,transaction_sha256=sha(encoded(tx)),
            expected_before_owners=current['owners'],face_readback=spec['face_readback'],parent_transactions=copy.deepcopy(parents),
            allow_known_mixed_on_first_apply=rollback)
  if rollback:plan['parent_transactions']['subtitle_submit_receipt']=dict(stage=STAGE,field='applied_spec_sha256',spec_sha256=sha(nraw),allowed_states=['INTENT','APPLIED'])
  save(direction+'_plan.json',plan)
 runner=(HERE/'tools/publish_single_projection.py').read_text('utf-8')
 for old,new in [("root=HERE/'package/single_projection'","root=HERE/'package/subtitle_receipt'"),
                 ("review['candidate_source_sha256']=='984d3ca24067bf5129e9ce3b0054f32cced717b6b8824eab347476bef2f9e502'", "review['candidate_source_sha256']=='de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2'"),
                 ("('single_projection_'+a.direction", "('subtitle_receipt_'+a.direction")]:
  assert runner.count(old)==1;runner=runner.replace(old,new,1)
 ast.parse(runner);runner_path=HERE/'tools/publish_subtitle_receipt.py'
 with runner_path.open('x',encoding='utf-8',newline='\n') as f:f.write(runner)
 put('source.patch',''.join(difflib.unified_diff(old_source.decode().splitlines(True),new_source.decode().splitlines(True),fromfile='before/'+SOURCE,tofile='after/'+SOURCE)).encode())
 report=dict(schema='aura-subtitle-one-source-publication-preparation-1',status='PREPARED_FOR_LOCAL_REVIEW_NOT_APPLIED',
             old_spec_sha256=sha(old_spec_raw),new_spec_sha256=sha(nraw),new_startup_sha256=sha(sraw),new_manifest_sha256=sha(mraw),
             source_before_sha256=sha(old_source),source_after_sha256=sha(new_source),changed_source=SOURCE,unchanged_components=379,
             configuration_sha256=spec['configuration_sha256'],camera_and_wide_firmware_unchanged=True,
             original_25_controller_and_all_pan_configurations_unchanged=True,source_scope='One-time current-owner submit receipt; existing TTL and invalidation retained',
             arm_evidence=str(args.arm_evidence),arm_evidence_sha256=sha(args.arm_evidence.read_bytes()),
             publisher=str(runner_path),publisher_sha256=sha(runner_path.read_bytes()),
             forward_stage=STAGE,rollback_stage=STAGE+'-rollback',normal_WM_DELETE_only=True,production_modified=False)
 save('PREPARATION.json',report)
 files={p.relative_to(OUT).as_posix():sha(p.read_bytes()) for p in OUT.rglob('*') if p.is_file()}
 files['../../tools/publish_subtitle_receipt.py']=sha(runner_path.read_bytes())
 save('BUNDLE_MANIFEST.json',dict(schema='aura-subtitle-publisher-bundle-1',status='PREPARED_NOT_APPLIED',files=files,
                                source=SOURCE,source_sha256=sha(new_source),new_spec_sha256=sha(nraw),new_startup_sha256=sha(sraw),new_manifest_sha256=sha(mraw)))
 print(json.dumps(dict(bundle=str(OUT),bundle_manifest_sha256=sha((OUT/'BUNDLE_MANIFEST.json').read_bytes()),**report)))

if __name__=='__main__':main()
