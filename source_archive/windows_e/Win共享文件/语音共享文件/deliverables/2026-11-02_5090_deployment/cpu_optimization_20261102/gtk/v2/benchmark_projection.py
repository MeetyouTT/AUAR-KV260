"""Synthetic state-copy CPU benchmark, not a whole-GTK or board saving claim."""
import argparse
import json
import platform
import statistics
import time
from projection_support import client,snapshot

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--iterations',type=int,default=3000);parser.add_argument('--rounds',type=int,default=4)
    args=parser.parse_args();assert 100<=args.iterations<=10000 and 2<=args.rounds<=6
    rows=[]
    for filled in (False,True):
        obj,_=client(filled=filled)
        for round_number in range(args.rounds):
            order=('full','preview') if round_number%2==0 else ('preview','full')
            for mode in order:
                method=obj.read if mode=='full' else obj.read_preview
                for _ in range(30):method()
                cpu=time.process_time_ns();wall=time.perf_counter_ns()
                for _ in range(args.iterations):method()
                wall=time.perf_counter_ns()-wall;cpu=time.process_time_ns()-cpu
                rows.append({'fixture':'populated_public' if filled else 'small_public','round':round_number+1,'mode':mode,
                    'iterations':args.iterations,'cpu_ns_per_read':cpu/args.iterations,'wall_ns_per_read':wall/args.iterations})
    summary=[]
    for label in ('small_public','populated_public'):
        medians={mode:statistics.median(row['cpu_ns_per_read'] for row in rows if row['fixture']==label and row['mode']==mode) for mode in ('full','preview')}
        summary.append({'fixture':label,**medians,'copy_cpu_reduction_percent':(medians['full']-medians['preview'])/medians['full']*100})
    print(json.dumps({'status':'PUBLIC_SNAPSHOT_CPU_BENCHMARK_COMPLETED','architecture':platform.machine(),'python_version':platform.python_version(),
        'iterations':args.iterations,'rounds':args.rounds,'rows':rows,'summary':summary,
        'scope':'State-read method only, fixed public source clock; not whole GTK CPU or board savings.',
        'camera_screen_models_database_motion_or_network_opened':False}))

if __name__=='__main__':main()
