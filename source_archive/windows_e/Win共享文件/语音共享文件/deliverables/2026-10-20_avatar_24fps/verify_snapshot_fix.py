from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE/'verify_stable_fps.py').read_text(encoding='utf-8')
s=s.replace("'stable_fps_candidate.json'","'snapshot_fix_candidate.json'").replace("'stable_fps_verification.json'","'snapshot_fix_verification.json'")
exec(compile(s,str(HERE/'verify_stable_fps.py'),'exec'))
