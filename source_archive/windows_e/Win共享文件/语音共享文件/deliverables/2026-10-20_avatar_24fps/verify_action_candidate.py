from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE/'verify_stable_fps.py').read_text(encoding='utf-8')
source=source.replace("'stable_fps_candidate.json'","'action_candidate.json'").replace("'stable_fps_verification.json'","'action_verification.json'")
exec(compile(source,str(HERE/'verify_stable_fps.py'),'exec'))
