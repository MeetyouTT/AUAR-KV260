from pathlib import Path
p = Path('E:/项目/共享文件夹/aura/board/interaction/qt_widgets.py')
s = p.read_text(encoding='utf-8')
start = s.index('    def _state_time(')
end = s.index('    def _sprite_sequence(', start)
reply = '''    @staticmethod
    def _reply_text(snap: typing.Dict) -> str:
        dialogue = snap.get("dialogue") if isinstance(snap, dict) else None
        text = dialogue.get("last_reply") if isinstance(dialogue, dict) else None
        return text if isinstance(text, str) else ""

'''
p.write_text(s[:start] + reply + s[end:], encoding='utf-8')
