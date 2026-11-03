from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE/'smoke_stable_fps.py').read_text(encoding='utf-8')
source=source.replace("'stable_fps_candidate.json'","'action_candidate.json'").replace("'stable_fps_smoke.json'","'action_smoke.json'")
exec(compile(source,str(HERE/'smoke_stable_fps.py'),'exec'))
