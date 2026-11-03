"""Run the current avatar UI with optional finite manual pan controls."""
import json
from pathlib import Path
import sys

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))


def main(argv=None):
    from tools import board_avatar_gtk
    from tools.pan_controls import stage_type
    from board.motion.manual import ManualPan
    from board.motion.manual_vsrv import ManualVSRV
    def factory():
        def transport():
            path = AURA/'config/pan_manual.local.json'
            if not path.is_file():
                raise ValueError('转轴未接入，请先完成板端接口配置')
            config = json.loads(path.read_text())
            if config.get('schema_version') != 1:
                raise ValueError('转轴接口配置版本不匹配')
            return ManualVSRV(config)
        return ManualPan(transport)
    original = board_avatar_gtk.BoardAvatarStage
    board_avatar_gtk.BoardAvatarStage = stage_type(original, factory)
    try:
        return board_avatar_gtk.main(argv)
    finally:
        board_avatar_gtk.BoardAvatarStage = original


if __name__ == '__main__':
    sys.exit(main())
