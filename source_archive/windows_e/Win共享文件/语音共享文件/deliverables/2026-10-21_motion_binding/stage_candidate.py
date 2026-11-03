import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'2026-10-20_avatar_24fps'
# Reuse the byte-preserving overlay builder, with this task's two new files.
s=(OLD/'prepare_action_candidate.py').read_text(encoding='utf-8')
s=s.replace("HERE=Path(__file__).resolve().parent;", "HERE=Path(%r);"%str(OLD))
s=s.replace("HERE/'action_sources'","Path(%r)"%str(HERE/'candidate_sources'))
s=s.replace("assert 'f8e48486023d' in str(source),'Actions require the pacing candidate to have passed first'", "assert 'candidate-fe6f5c7b1b56' in str(source),'Production changed; rebase required'")
s=s.replace("assert (source.parent/'committed').is_file(),'Render candidate not committed'", "assert (source/'aura/tools/render_performance.py').is_file(),'Phase logging missing'")
s=s.replace("HERE/'action_candidate.json'","Path(%r)"%str(HERE/'candidate.json'))
exec(compile(s,str(OLD/'prepare_action_candidate.py'),'exec'))
