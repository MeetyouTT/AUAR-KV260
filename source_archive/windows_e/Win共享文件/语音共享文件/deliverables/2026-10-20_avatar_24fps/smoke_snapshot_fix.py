from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'smoke_stable_fps.py').read_text(encoding='utf-8')
s=s.replace("'stable_fps_candidate.json'","'snapshot_fix_candidate.json'").replace("'stable_fps_smoke.json'","'snapshot_fix_smoke.json'")
exec(compile(s,str(HERE/'smoke_stable_fps.py'),'exec'))
