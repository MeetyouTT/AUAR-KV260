"""Runnable formal Qt UI with the production event bus, FSM and shared player.

F1: listen; F2: wake; F3: mock neutral reply; Escape: cancel.
--selftest uses offscreen rendering and writes a 1024x600 snapshot.
"""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--outdir', default=str(ROOT / 'docs/demo_qt'))
    args = ap.parse_args()
    if args.selftest:
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtGui import QKeySequence, QShortcut
    from PySide6.QtWidgets import QApplication
    from board.runtime.event_bus import EventBus, EventEnvelope
    from board.runtime.events import EventType as E
    from board.runtime.fsm import RuntimeFSM
    from board.interaction.ui_state import UiState
    from board.interaction.qt_app import MainWindow
    app = QApplication.instance() or QApplication([])
    bus = EventBus(dispatch_async=False)
    fsm = RuntimeFSM(bus=bus)
    ui = UiState(event_bus=bus)
    window = MainWindow(ui, event_bus=bus)
    def send(event, payload=None):
        bus.publish(EventEnvelope(event, 'qt_demo', 0, payload or {}))
    def reply():
        send(E.BOARD_KEY_PRESSED)
        send(E.AUDIO_VAD_END)
        send(E.DIALOGUE_RESPONSE_RECEIVED, {'reply_text': '你好，很高兴见到你。', 'emotion': 'neutral'})
    callbacks = {'F1': lambda: send(E.BOARD_KEY_PRESSED),
                 'F2': lambda: send(E.AUDIO_KWS_DETECTED), 'F3': reply,
                 'Escape': lambda: send(E.AUDIO_CANCEL_REQUESTED)}
    shortcuts = []
    for key, callback in callbacks.items():
        shortcut = QShortcut(QKeySequence(key), window)
        shortcut.activated.connect(callback)
        shortcuts.append(shortcut)
    if args.selftest:
        out = Path(args.outdir)
        out.mkdir(parents=True, exist_ok=True)
        reply()
        window.render_to_file(str(out / 'qt_shared_player.png'))
        assert fsm.state.value == 'SPEAKING_NEUTRAL'
        assert window.avatar_panel._last_meta['asset'] == 'talking_neutral'
        window._timer.stop()
        print('QT SELFTEST OK: actual MainWindow / EventBus / shared AvatarPlayer')
        return 0
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
