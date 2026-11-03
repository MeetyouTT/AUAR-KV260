"""Real Tk event loop: full 66-second script, then invoke Replay and inspect traces."""
import hashlib
import json
import random
import sys
from pathlib import Path
import tkinter as tk

AURA = Path(r'E:\项目\共享文件夹\aura')
sys.path.insert(0, str(AURA))
from tools import demo_script as demo
from board.interaction.avatar_player import AvatarPlayer

OUT = Path(__file__).parent
rows = []
original_sample = demo.ScriptRunner._sample
original_tk = tk.Tk
replayed = []

def sample(runner, t):
    meta = original_sample(runner, t)
    if meta is not None:
        rows.append(dict(t=round(t, 4), run=len(replayed), state=core.fsm.state.label,
                         **{k:meta[k] for k in ['display_state', 'transitioning', 'stage', 'asset', 'index']}))
    return meta

def create_root():
    root = original_tk()
    root.withdraw()                 # exercise the actual widgets without opening a test window
    def replay():
        buttons = [w for frame in root.winfo_children() for w in frame.winfo_children()
                   if isinstance(w, tk.Button)]
        assert len(buttons) == 1
        replayed.append(True)
        buttons[0].invoke()
    root.after(66800, replay)
    root.after(68600, root.destroy)
    return root

demo.ScriptRunner._sample = sample
tk.Tk = create_root
core = AvatarPlayer(rng=random.Random(7))
trace = demo.run_window(core)
first = [r for r in rows if r['run'] == 0]
second = [r for r in rows if r['run'] == 1]
states = {r['state'] for r in first}
checks = dict(
    replay_no_script_errors=not trace.errors,
    replay_no_rejected_events=not trace.rejected,
    wake_to_listening=any(6.3 < r['t'] < 8.5 and r['state'] == 'LISTENING' for r in first),
    nod_to_speaking=any(40.3 < r['t'] < 43.5 and r['display_state'] == 'SPEAKING' for r in first),
    all_speech_emotions={'SPEAKING', 'SPEAKING_NEUTRAL', 'SPEAKING_LOW'} <= states,
    stop_retains_exit=any(14.9 <= r['t'] < 15.5 and r['transitioning'] and r['display_state'] == 'SPEAKING_NEUTRAL' for r in first),
    cancel_retains_exit=any(59 <= r['t'] < 61 and r['transitioning'] and r['display_state'] == 'SPEAKING' for r in first),
    finished_idle=bool(first) and first[-1]['state'] == 'IDLE',
    replay_after_finished=bool(second) and all(r['state'] == 'IDLE' and r['display_state'] == 'IDLE' for r in second),
    replay_trace_cleared=bool(trace.samples) and trace.samples[-1]['t'] < 3,
)
report = dict(checks=checks, first_samples=len(first), replay_samples=len(second),
              cue_count=len(demo.SCRIPT), errors=trace.errors, rejected=trace.rejected)
(OUT/'window_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'window_frames.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
assert all(checks.values()), report
