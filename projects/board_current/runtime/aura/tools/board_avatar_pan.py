"""Run the current avatar UI with optional finite manual pan controls."""
import json
from pathlib import Path
import sys

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))


def main(argv=None):
    from tools import board_avatar_gtk
    from tools.face_pan_controls import stage_type, FacePanProcess
    from board.motion.manual_process import ManualPanProcess
    def factory():
        path = AURA/'config/pan_manual.local.json'
        config = json.loads(path.read_text()) if path.is_file() else {}
        return FacePanProcess(config)
    original = board_avatar_gtk.BoardAvatarStage
    board_avatar_gtk.BoardAvatarStage = stage_type(original, factory)
    try:
        return board_avatar_gtk.main(argv)
    finally:
        board_avatar_gtk.BoardAvatarStage = original


if __name__ == '__main__':
    sys.exit(main())
