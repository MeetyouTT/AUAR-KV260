from pathlib import Path
import shutil

root = Path('E:/项目/共享文件夹/aura')
backup = Path(__file__).resolve().parent / 'before'
for rel in ['tools/demo_stage.py', 'board/interaction/qt_widgets.py',
            'board/interaction/qt_app.py', 'board/interaction/ui_state.py',
            'board/interaction/avatar_lod.py', 'board/interaction/avatar_board.py',
            'scripts/board_export.py', 'ui/avatar_board_manifest.json',
            'board/interaction/lvgl/avatar_assets_table.h', 'tools/run_tests_light.py',
            'tests/test_avatar_b2.py', 'tests/test_avatar_board.py',
            'tests/test_avatar_lod.py', 'README.md', '.cline-handover.md']:
    dest = backup / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / rel, dest)
p = root / 'tools/demo_stage.py'
s = p.read_text(encoding='utf-8')
start = s.index('class StageCore:')
end = s.index('# --------------------------------------------------------------------------- #\n# 语音输入', start)
body = s[start:end].replace('class StageCore:', 'class AvatarPlayer:', 1)
header = '''# -*- coding: utf-8 -*-
"""Shared avatar playback core for Tk and Qt; independent of both UI toolkits."""
from __future__ import annotations
import typing
from PIL import Image
from . import avatar_assets, avatar_timing
from board.runtime.event_bus import EventEnvelope
from board.runtime.events import EventType
from board.runtime.fsm import RuntimeFSM

'''
(root / 'board/interaction/avatar_player.py').write_text(header + body, encoding='utf-8')
s = s[:start] + 'from board.interaction.avatar_player import AvatarPlayer as StageCore\n\n\n' + s[end:]
p.write_text(s, encoding='utf-8')
print('Shared player extracted; original source backups saved.')
