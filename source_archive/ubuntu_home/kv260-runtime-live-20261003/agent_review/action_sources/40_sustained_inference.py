# SPDX-License-Identifier: MIT
# At least 1800 monotonic seconds, one synchronous inference per iteration.
p=Path(CFG.get('agent_helpers',str(WORK/'agent_helpers.py')))
assert digest(p)==CFG['agent_helpers_sha256']
exec(compile(p.read_bytes(),str(p),'exec'))
begin_phase('40-sustained-inference')
guard(CFG['fixed_srcversion'],OFFICIAL_APP)
manager_guard(True)
duration=float(CFG.get('sustained_seconds',1800))
interval=float(CFG.get('sample_interval_seconds',30))
assert duration>=1800 and 0<interval<=60
dpu_query(OFFICIAL_APP,'initial-query')
started=time.monotonic()
next_sample=started
iterations=0
samples=[]
while time.monotonic()-started<duration:
    iterations+=1
    classify(OFFICIAL_APP,'inference-{:06d}'.format(iterations))
    now=time.monotonic()
    if now>=next_sample:
        label='sample-{:04d}'.format(len(samples))
        row=sample(label)
        row['elapsed_seconds']=now-started
        row['inferences_completed']=iterations
        kernel_check(label)
        samples.append(row)
        write_json(_phase/'progress.json',{'duration_target_seconds':duration,
            'elapsed_seconds':now-started,'inferences_completed':iterations,'latest_sample':row})
        print('SUSTAINED_SAMPLE '+json.dumps(row),flush=True)
        next_sample=now+interval
    time.sleep(min(1.0,max(0,duration-(time.monotonic()-started))))
guard(CFG['fixed_srcversion'],OFFICIAL_APP)
manager_guard(True)
dpu_query(OFFICIAL_APP,'final-query')
elapsed=time.monotonic()-started
row=sample('final')
row.update(elapsed_seconds=elapsed,inferences_completed=iterations)
kernel_check('final')
samples.append(row)
assert elapsed>=1800 and iterations>0
finish_phase({'elapsed_seconds':elapsed,'inferences_completed':iterations,
    'sample_interval_seconds':interval,'samples':samples,'all_top5_match':True,
    'limitation':'Finite observation; no claim of universal absence of memory leaks or FPS benchmark'})
