import hashlib,importlib.util
from pathlib import Path
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/gui-lifecycle-v2')
assert hashlib.sha256((p/'gui_lifecycle_deploy.py').read_bytes()).hexdigest()=='5d934d3ce07fdb52f18f63dd3be2215daaea90898ca45cc1288e85f5fd5041ba'
assert hashlib.sha256((p/'gui-patch-manifest.json').read_bytes()).hexdigest()=='e09a7bb164544737f927ff0820da526f36fd285b3106eb8a3f47c44595f6e428'
s=importlib.util.spec_from_file_location('gui_lifecycle_deploy',p/'gui_lifecycle_deploy.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.main('install')
