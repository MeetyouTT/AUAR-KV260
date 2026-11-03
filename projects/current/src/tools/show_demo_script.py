"""Open the current scripted demo at the front of the user's desktop."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.demo_script import main


def run():
    args = sys.argv[1:]
    if '--qt-window' in args:
        return main(args)
    import tkinter as tk
    original_tk = tk.Tk

    def front_window(*args, **kwargs):
        root = original_tk(*args, **kwargs)
        root.geometry('+80+80')
        root.attributes('-topmost', True)
        root.after_idle(root.lift)
        root.after(200, root.focus_force)
        root.after(1500, lambda: root.attributes('-topmost', False))
        return root

    tk.Tk = front_window
    try:
        return main(['--window', *args])
    finally:
        tk.Tk = original_tk


if __name__ == '__main__':
    raise SystemExit(run())
