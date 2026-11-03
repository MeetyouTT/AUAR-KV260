CONFIG='/home/root/aura-video-cpu-20261023/66cde810eb059dce/startup/config.json'
import hashlib,json
from pathlib import Path
config=json.loads(Path(CONFIG).read_text());root=Path(config['runtime'])/'aura'
actual=hashlib.sha256((root/'tools/board_avatar_gtk.py').read_bytes()).hexdigest()
print(json.dumps({'actual_gui_sha':actual,'gui_sha_field':config.get('gui_sha256'),'component_pin':config.get('component_sha256',{}).get('tools/board_avatar_gtk.py'),'target_main_name':str(root/'tools/board_avatar_gtk.py'),'config_keys':list(config),'no_modification':True}))
