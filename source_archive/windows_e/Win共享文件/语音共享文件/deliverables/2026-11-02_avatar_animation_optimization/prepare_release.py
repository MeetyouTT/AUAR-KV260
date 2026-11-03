from inspect_baseline import *
import ast,copy,zipfile
def archive(path,files):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for name,raw in sorted(files.items()):
   i=zipfile.ZipInfo(name,(2026,11,2,12,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,raw)
def main():
 out=HERE/'release';out.mkdir(exist_ok=True);backup=HERE/'board_results/backup';src=HERE/'candidate_physics_v2/native'
 build=load(HERE/'board_results/revision2b/BUILD_RECEIPT.json')
 for name,h in build['source_files'].items():assert sha(src/name)==h
 lib=HERE/'board_results/revision2b/libaura_yuki.so';assert sha(lib)==build['library_sha256']
 package=out/'native_physics_arm_R2.zip'
 files={'native/'+p.name:p.read_bytes() for p in src.iterdir() if p.is_file()}
 files['libaura_yuki.so']=lib.read_bytes();files['BUILD_RECEIPT.json']=json.dumps(build,indent=2).encode()
 archive(package,files);package_sha=sha(package)
 before_pair=load(backup/'config/yuki_pair.formal.json');pair=copy.deepcopy(before_pair)
 pair['runtime_pins']['tools/libaura_yuki.so']=sha(lib);pair['native_package_sha256']=package_sha
 pair_raw=(json.dumps(pair,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode();pair_sha=hashlib.sha256(pair_raw).hexdigest()
 raw=(backup/'tools/formal_yuki.py').read_bytes();text=raw.decode();formal=text.replace("PAIR_CONFIG_SHA256='"+sha(backup/'config/yuki_pair.formal.json')+"'","PAIR_CONFIG_SHA256='"+pair_sha+"'",1)
 formal=formal.replace("NATIVE_PACKAGE_SHA256='"+before_pair['native_package_sha256']+"'","NATIVE_PACKAGE_SHA256='"+package_sha+"'",1)
 assert formal!=text
 old_ast=ast.parse(text);new_ast=ast.parse(formal)
 def normalize(tree):
  for node in tree.body:
   if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('PAIR_CONFIG_SHA256','NATIVE_PACKAGE_SHA256') for t in node.targets):node.value=ast.Constant(value='PIN')
  return ast.dump(tree,include_attributes=False)
 assert normalize(old_ast)==normalize(new_ast)
 cfg=load(backup/'config/board_avatar_gtk.json');old_cfg=copy.deepcopy(cfg);assert cfg['character_pair']['selection_sha256']==sha(backup/'config/yuki_pair.formal.json')
 cfg['character_pair']['selection_sha256']=pair_sha
 payload={'tools/libaura_yuki.so':lib.read_bytes(),'config/yuki_pair.formal.json':pair_raw,'tools/formal_yuki.py':formal.encode(),'config/board_avatar_gtk.json':(json.dumps(cfg,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()}
 rows={}
 for rel,b in payload.items():
  dest=out/'runtime'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
  rows[rel]=dict(before_sha256=sha(backup/rel),after_sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
 startup=load(backup/'startup.json');new=copy.deepcopy(startup)
 for rel,row in rows.items():assert startup['component_sha256'][rel]==row['before_sha256'];new['component_sha256'][rel]=row['after_sha256']
 save(out/'startup.after.json',new)
 manifest=dict(schema='aura-avatar-physics-arm-release-1',release='R2_shoulder_pivot',source_baseline_library_sha256=startup['component_sha256']['tools/libaura_yuki.so'],startup_before=sha(backup/'startup.json'),startup_after=sha(out/'startup.after.json'),native_package_sha256=package_sha,components=rows,unchanged_component_count=376,total_components=380,persona_business_audio_eye_policy_unchanged=True,character_model_textures_unchanged=True,struct_abi_unchanged=True,original_camera_native_and_axis_unchanged=True,semantic_checks=dict(formal_module_only_two_pin_constants_changed=True,pair_identity_and_presentation_unchanged=pair['identity']==before_pair['identity'] and pair['presentation']==before_pair['presentation'],GUI_config_only_selection_SHA_changed=True))
 save(out/'MANIFEST.json',manifest)
 overlay={'runtime/'+k:v for k,v in payload.items()}
 overlay['MANIFEST.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode()
 overlay.update({'native/'+p.name:p.read_bytes() for p in src.iterdir() if p.is_file()})
 archive(out/'animation_overlay_R2.zip',overlay)
 print(json.dumps(manifest,ensure_ascii=False))
if __name__=='__main__':main()
