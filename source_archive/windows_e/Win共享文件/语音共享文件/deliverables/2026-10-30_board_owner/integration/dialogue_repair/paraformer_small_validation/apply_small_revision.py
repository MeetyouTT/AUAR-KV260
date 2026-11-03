"""Use the normal-closed publisher with an explicit, fixed pair of approved ASR variants."""
import ast
import hashlib
import importlib.util
from pathlib import Path

HERE=Path(__file__).resolve().parent
path=HERE.parent.parent/'listening_entry_fix/apply_closed_revision.py'
assert hashlib.sha256(path.read_bytes()).hexdigest()=='74bd266353d58f7edd8728ef0dd1ae1ab613eb8386884bba32940018b510bfe2'
spec=importlib.util.spec_from_file_location('_reviewed_closed_asr_publisher',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
old="assert set(REVISION['business_options'])<=set(('frontend_process','frontend_capture_process','frontend_optimization','capture_priority_nice','frontend_threads','asr_threads'))"
new=r'''
assert set(REVISION['business_options'])<=set(('frontend_process','frontend_capture_process','frontend_optimization','capture_priority_nice','frontend_threads','asr_threads','dialogue_output_format','asr_variant','asr_directory'))
options=REVISION['business_options']
assert options.get('dialogue_output_format','json') in ('json','dialogue_abc_v1')
choices={
 'baseline':('/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/models/paraformer',
  'f36a0433bcf096bd6d6f11b80a3ac8bed110bdca632fe0d731df8d1a84475945','59aba8873a2ed1e122c25fee421e25f283b63290efbde85c1f01a853d83cb6e6'),
 'paraformer_small':('/home/root/aura-board-asr-models/paraformer-small-63ddc3cd0f2810b6',
  '3ef6c19369b912f7caf3cef8e545c5ccd1a33d9d7ec792a46668dc41c4b229ec','4b2d964e18b9cf139b473003b6698fb2ed9a2a5ec55b93daa677b28f578897aa')}
variant=options.get('asr_variant')
assert isinstance(variant,str) and variant in choices
directory,model_pin,tokens_pin=choices[variant]
assert options.get('asr_directory')==directory and options.get('asr_threads')==3
for name,pin in (('model.int8.onnx',model_pin),('tokens.txt',tokens_pin)):
 resource=Path(directory)/name
 assert resource.is_file() and not any(p.is_symlink() for p in (resource,*resource.parents))
 assert 0<resource.stat().st_size<=300*1024*1024
 digest=hashlib.sha256()
 with resource.open('rb') as model_file:
  for block in iter(lambda:model_file.read(1048576),b''):digest.update(block)
 assert digest.hexdigest()==pin
'''
assert module.REMOTE.count(old)==1
module.REMOTE=module.REMOTE.replace(old,new)
ast.parse(module.REMOTE,feature_version=(3,9))

if __name__=='__main__':module.main()
