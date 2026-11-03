"""Use existing camera/model owners with anonymous face edge observations."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
meta = json.loads((ROOT.parent/'meta.json').read_text())
sys.path.insert(0, str(Path(meta['candidate_root'])/'aura'))
sys.path.insert(0, str(ROOT))
from board.vision import ui_camera_service as camera
from board.motion.camera_feed import install as install_body_observation
from motion_stream import install as install_body_stream
from face_source import install as install_face_source
install_body_observation(camera)
install_body_stream(camera)
install_face_source(camera, interval_ms=100, optical_flow=True)
camera.main()
