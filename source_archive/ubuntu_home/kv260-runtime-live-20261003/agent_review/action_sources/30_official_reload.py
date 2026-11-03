# SPDX-License-Identifier: MIT
# Executed after fresh hash-locked live_common.py; no automatic restart.
p=Path(CFG.get('agent_helpers',str(WORK/'agent_helpers.py')))
assert digest(p)==CFG['agent_helpers_sha256']
exec(compile(p.read_bytes(),str(p),'exec'))
begin_phase('30-official-reload')
cycles=[]
for cycle in range(1,31):
    guard(CFG['fixed_srcversion'],OFFICIAL_APP)
    manager_guard(True)
    run_logged(['dfx-mgr-client','-remove'],'cycle-{:02d}-remove'.format(cycle))
    guard(CFG['fixed_srcversion'],None)
    manager_guard(True)
    kernel_check('cycle-{:02d}-removed'.format(cycle))
    run_logged(['dfx-mgr-client','-load',OFFICIAL_APP],'cycle-{:02d}-load'.format(cycle))
    guard(CFG['fixed_srcversion'],OFFICIAL_APP)
    manager_guard(True)
    kernel_check('cycle-{:02d}-loaded'.format(cycle))
    dpu_query(OFFICIAL_APP,'cycle-{:02d}-query'.format(cycle))
    result=classify(OFFICIAL_APP,'cycle-{:02d}-classification'.format(cycle))
    row={'cycle':cycle,'top5':result,'sample':sample('cycle-{:02d}'.format(cycle))}
    kernel_check('cycle-{:02d}-functional'.format(cycle))
    cycles.append(row)
    write_json(_phase/'progress.json',{'completed_cycles':len(cycles),'cycles':cycles})
    print('OFFICIAL_RELOAD '+json.dumps(row),flush=True)
finish_phase({'cycles':30,'all_top5_match':True,'all_dpu_match':True,'samples':cycles})
