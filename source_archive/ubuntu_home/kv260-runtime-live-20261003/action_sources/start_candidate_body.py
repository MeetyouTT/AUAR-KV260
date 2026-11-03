# Temporary use of the two exact binaries that passed previous board tests.
guard(CFG['stock_srcversion'],'kv260-benchmark-b4096')
manager_guard(False)
assert not Path(CFG['override']).exists()
assert not Path(CFG['override']).parent.exists()
assert digest(CFG['candidate_manager'])==CFG['manager_sha256']
assert digest(CFG['candidate_module'])==CFG['module_sha256']
before=snapshot('before-original-remove')
run(['dfx-mgr-client','-remove'])
guard(CFG['stock_srcversion'],None)
assert not Path('/sys/bus/platform/devices/axi:zyxclmm_drm').exists()
after=snapshot('after-original-remove')
old=Path(before['kernel_log']).read_text().splitlines()
new=Path(after['kernel_log']).read_text().splitlines()
assert new[:len(old)]==old,'Kernel log continuity lost during original remove'
errors=[s for s in new[len(old):] if re.search(r'BUG:|Oops:|Kernel panic|ERROR|expected refcount',s)]
assert len(errors)<=1 and all('expected refcount 1 instead of 2' in s and '/axi/zyxclmm_drm' in s for s in errors),errors
(WORK/'original-remove-review.json').write_text(json.dumps({'new_error_lines':errors,'allowed_once_known_stock_error':True},indent=2))
run(['rmmod','zocl'])
guard(None,None)
run(['insmod',CFG['candidate_module'],'enable_xgq_ert=1'])
guard(CFG['fixed_srcversion'],None)
run(['systemctl','stop','dfx-mgr.service'])
assert manager_pid()==0
override=Path(CFG['override'])
assert not override.exists() and not override.parent.exists()
override.parent.mkdir()
with override.open('x') as stream:stream.write(CFG['override_text'])
assert digest(override)==CFG['override_text_sha256']
run(['systemctl','daemon-reload'])
run(['systemctl','start','dfx-mgr.service'])
wait_manager(True)
guard(CFG['fixed_srcversion'],'kv260-benchmark-b4096')
assert watches()==CFG['expected_watches']
final=snapshot('candidate-started')
final_lines=Path(final['kernel_log']).read_text().splitlines()
assert final_lines[:len(new)]==new,'Kernel log continuity lost during candidate start'
new_errors=[s for s in final_lines[len(new):] if re.search(r'BUG:|Oops:|Kernel panic|ERROR|expected refcount',s)]
assert not new_errors,new_errors
print('CANDIDATE_STARTED '+json.dumps({'pid':manager_pid(),'driver':CFG['fixed_srcversion'],'watches':watches()}),flush=True)
