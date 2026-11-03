"""Restore only this update's backup if its GUI cannot become ready."""
import json
from pathlib import Path
import runpy

stage=Path('/home/root/aura-ui-layers-20261016/update-c2ce862bbed8ecb2')
namespace=runpy.run_path(str(stage/'payload/board_deploy.py'))
assert namespace['sha'](namespace['UNIT'])==namespace['MANIFEST']['files']['startup/aura-avatar-ui.service']['sha256']
namespace['run'](['systemctl','stop','aura-avatar-ui.service'])
print(json.dumps({'status':'RESTORED_PREVIOUS_GUI','rollback':namespace['restore']()}))
