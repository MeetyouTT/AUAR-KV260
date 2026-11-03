"""Local-only compact, atomic coordination receipt; no device connections."""
from pathlib import Path
import argparse,datetime,json,os

p=argparse.ArgumentParser();p.add_argument('--status',required=True);p.add_argument('--phase',required=True)
p.add_argument('--sampler',type=int);p.add_argument('--case',type=int);p.add_argument('--index',type=int)
p.add_argument('--idle',action='store_true');args=p.parse_args()
ab=Path(__file__).parent;base=ab.parent.parent
path=base.parent/'2026-10-30_board_owner/coordination/character_ack.json'
x=json.loads(path.read_text(encoding='utf-8-sig'));now=datetime.datetime.now(datetime.timezone.utc).isoformat()
x.update(status=args.status,updated_at_utc=now,written_at_utc=now)
w=x['resource_windows'];w.update(current_phase=args.phase,board_sampler_pid=args.sampler,board_case_pid=args.case,
    active_board_cpu_gpu_tests=not args.idle,active_performance_sampling=not args.idle,
    all_character_validation_processes_exited=args.idle,formal_case_index=args.index,
    isolated_windows_server_pid=4088,isolated_windows_server_port=54283)
t=path.with_suffix('.tmp');t.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(t,path)
print(json.dumps(dict(status=args.status,board_sampler_pid=args.sampler,board_case_pid=args.case,index=args.index)))
