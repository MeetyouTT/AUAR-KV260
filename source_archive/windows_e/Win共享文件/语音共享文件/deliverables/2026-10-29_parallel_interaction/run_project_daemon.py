"""Independent one-shot project daemon creator with the reviewed local policy."""
import argparse,json,os,runpy,traceback
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]
p=argparse.ArgumentParser();p.add_argument('--receipt',default='layout_daemon_start.json');args=p.parse_args()
assert '/' not in args.receipt and '\\' not in args.receipt
try:
    before=json.loads((H/'runtime_owners_before.json').read_text(encoding='utf-8-sig'))['11435']
    os.environ['PATH']=str(Path(before['exe']).parent)+os.pathsep+os.environ.get('PATH','')
    module=runpy.run_path(str(P/'deliverables/2026-10-18_board_dialogue/project_ollama.py'))
    value=module['ensure']()
except BaseException as exc:value={'status':'FAILED','error':type(exc).__name__+': '+str(exc),'traceback':traceback.format_exc()}
(H/args.receipt).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
