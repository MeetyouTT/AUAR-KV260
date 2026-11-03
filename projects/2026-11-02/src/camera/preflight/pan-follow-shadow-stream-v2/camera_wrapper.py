"""Use the existing camera and native owner with a bounded observation stream."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
OPS = ROOT.parent
meta = json.loads((OPS / 'meta.json').read_text())
sys.path.insert(0, str(Path(meta['candidate_root']) / 'aura'))
sys.path.insert(0, str(ROOT))
from board.vision import ui_camera_service
from board.motion.camera_feed import install as install_observation
from motion_stream import install as install_stream

install_observation(ui_camera_service)
install_stream(ui_camera_service)
ui_camera_service.main()
