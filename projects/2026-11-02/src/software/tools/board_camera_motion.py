"""Run the existing camera service with its optional read-only motion feed."""
import sys
from pathlib import Path

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))


def main():
    from board.vision import ui_camera_service
    from board.motion.camera_feed import install
    install(ui_camera_service)
    ui_camera_service.main()


if __name__ == '__main__':
    main()
