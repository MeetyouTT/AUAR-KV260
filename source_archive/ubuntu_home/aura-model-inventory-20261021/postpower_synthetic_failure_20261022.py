import json
from pathlib import Path
p=Path('/home/root/aura-post-power-20261022/synthetic/fae37bfe9b095077/results')
print(json.dumps({'tests_stderr':(p/'tests.stderr.txt').read_text()[-5000:],'kernel':json.loads(Path('/home/root/aura-dpu-vision-20261021/runtime/81fdb11903abb71e-live-134783/board_camera_ui.json').read_text()).get('capture_fps')}))
