from common import *
import ast,zipfile,copy
def archive(p,files):
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
  for n,data in sorted(files.items()):
   i=zipfile.ZipInfo(n,(2026,11,2,12,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,data)
def main():
 out=HERE/'release';out.mkdir(exist_ok=True);b=HERE/'board_results/backup';source=HERE/'candidate/native';build=load(HERE/'board_results/build/BUILD_RECEIPT.json');lib=HERE/'board_results/build/libaura_yuki.so'
 assert sha(lib)==build['library_sha256']
 for n,h in build['source_files'].items():assert sha(source/n)==h
 package=out/'native_natural_lower_arm_R3.zip';files={'native/'+p.name:p.read_bytes() for p in source.iterdir() if p.is_file()};files['libaura_yuki.so']=lib.read_bytes();files['BUILD_RECEIPT.json']=json.dumps(build,indent=2).encode();archive(package,files)
 old_pair=load(b/'config/yuki_pair.formal.json');pair=copy.deepcopy(old_pair);pair['runtime_pins']['tools/libaura_yuki.so']=sha(lib);pair['native_package_sha256']=sha(package)
 pair_raw=(json.dumps(pair,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode();pair_sha=hashlib.sha256(pair_raw).hexdigest()
 old=(b/'tools/formal_yuki.py').read_text(encoding='utf8');new=old.replace("PAIR_CONFIG_SHA256='"+sha(b/'config/yuki_pair.formal.json')+"'","PAIR_CONFIG_SHA256='"+pair_sha+"'",1).replace("NATIVE_PACKAGE_SHA256='"+old_pair['native_package_sha256']+"'","NATIVE_PACKAGE_SHA256='"+sha(package)+"'",1)
 def semantic(text):
  tree=ast.parse(text)
  for n in tree.body:
   if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('PAIR_CONFIG_SHA256','NATIVE_PACKAGE_SHA256') for t in n.targets):n.value=ast.Constant(value='PIN')
  return ast.dump(tree,include_attributes=False)
 assert old!=new and semantic(old)==semantic(new)
 gui=load(b/'config/board_avatar_gtk.json');assert gui['character_pair']['selection_sha256']==sha(b/'config/yuki_pair.formal.json');gui['character_pair']['selection_sha256']=pair_sha
 payload={'tools/libaura_yuki.so':lib.read_bytes(),'config/yuki_pair.formal.json':pair_raw,'tools/formal_yuki.py':new.encode(),'config/board_avatar_gtk.json':(json.dumps(gui,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()}
 rows={}
 for rel,data in payload.items():
  p=out/'runtime'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);rows[rel]=dict(before_sha256=sha(b/rel),after_sha256=sha(p),bytes=len(data))
 original=load(b/'startup.json');updated=copy.deepcopy(original)
 for rel,row in rows.items():assert original['component_sha256'][rel]==row['before_sha256'];updated['component_sha256'][rel]=row['after_sha256']
 save(out/'startup.after.json',updated)
 manifest=dict(schema='aura-natural-lower-arm-R3-release-1',release='R3_smaller_slower_lower_arm',startup_before=sha(b/'startup.json'),startup_after=sha(out/'startup.after.json'),native_package_sha256=sha(package),components=rows,total_components=380,unchanged_component_count=376,changed_behavior='Only lower/back arm angle, speed and damping; R2 shoulder compensation and other animation channels preserved',character_model_textures_business_audio_identity_memory_unchanged=True,source_files=build['source_files'])
 save(out/'MANIFEST.json',manifest);print(json.dumps(manifest))
if __name__=='__main__':main()
