import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;APP=HERE.parents[1]/'aura'
names=('common/speech_motion.py','common/voice_channel.py','tools/voice_channel_source.py')
report={'files':{name:{'before_sha256':hashlib.sha256((APP/name).read_bytes()).hexdigest(),
                       'after_sha256':hashlib.sha256((HERE/'action_sources'/name).read_bytes()).hexdigest()}
                 for name in names},'config_sha256':{}}
for name in ('config/voice_latency.json','config/board_dialogue_model.json','config/model_storage.local.json'):
    report['config_sha256'][name]=hashlib.sha256((APP/name).read_bytes()).hexdigest()
(HERE/'pc_action_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PC action source/config manifest prepared')
