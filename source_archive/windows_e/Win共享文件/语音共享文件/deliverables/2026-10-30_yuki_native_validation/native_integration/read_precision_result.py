from pathlib import Path
root=Path('/home/root/aura-yuki-validation-20261030/native_integration/results')
for name in ('precision-validation-result.json','precision-images.json'):
    path=root/name
    if path.exists():print(name,path.read_text()[:14000])
path=root/'precision-validation.log'
if path.exists():print('LOG_TAIL',path.read_text()[-5000:])
