# SPDX-License-Identifier: MIT
# Inspect actual state; normal unload only. No stock executable/module overwrite.
p=Path(CFG.get('agent_helpers',str(WORK/'agent_helpers.py')))
assert digest(p)==CFG['agent_helpers_sha256']
exec(compile(p.read_bytes(),str(p),'exec'))
recovery_diagnostics=[]
_strict_kernel_check=kernel_check
def kernel_check(label,initialize=False,allow_stock_remove=False):
    try:
        return _strict_kernel_check(label,initialize=initialize,allow_stock_remove=allow_stock_remove)
    except RuntimeError as error:
        # Diagnostic evidence may make the experiment fail, but it must not
        # block guarded baseline recovery. Occupancy/hash/identity guards below
        # remain strict and are not caught here.
        path=_phase/(label+'.kernel-review.json')
        evidence=json.loads(path.read_text()) if path.exists() else None
        row={'stage':label,'error':str(error),'kernel_review':evidence}
        recovery_diagnostics.append(row)
        write_json(_phase/'recovery-diagnostics.json',recovery_diagnostics)
        return evidence
begin_phase('60-restore')
service='dfx-mgr.service'
_original_active_packages=active_packages
def active_packages():
    if manager_pid()>0:
        return _original_active_packages()
    # No IPC query is possible while the daemon is stopped. Prove absence of
    # this run's ZOCL overlay from actual device-tree/platform state instead.
    assert not Path('/sys/bus/platform/devices/axi:zyxclmm_drm').exists(),'Manager stopped with ZOCL platform device present'
    assert not Path('/proc/device-tree/fpga-full/firmware-name').exists(),'Manager stopped with firmware overlay present'
    return []
override=Path(CFG['override'])
assert override.is_absolute() and str(override).startswith('/run/systemd/system/dfx-mgr.service.d/')
candidate=Path(CFG.get('candidate_manager',str(WORK/'candidate-stage/dfx-mgrd')))
assert candidate.is_relative_to(WORK) if hasattr(candidate,'is_relative_to') else str(candidate).startswith(str(WORK)+'/')
assert digest(candidate)==CFG['manager_sha256']
mod_version=Path('/sys/module/zocl/srcversion')
driver=mod_version.read_text().strip() if mod_version.exists() else None
assert driver in [None,CFG['fixed_srcversion'],CFG['stock_srcversion']]
current=active_packages()
assert current in [[],[(OFFICIAL_APP,0)],[(M3_APP,0)]],'Unexpected app; recovery stops'
assert driver is not None or not current,'Active app exists without driver'
app=current[0][0] if current else None
guard(driver,app)
pid=manager_pid()
if pid:
    exe=os.readlink('/proc/{}/exe'.format(pid))
    assert exe in [str(candidate),'/usr/bin/dfx-mgrd'],'Unexpected daemon'
    assert digest(exe)==(CFG['manager_sha256'] if exe==str(candidate) else CFG['stock_hashes26']['/usr/bin/dfx-mgrd'])
else:
    exe=None
if current:
    assert pid>0,'Cannot normally remove app without manager'
    run_logged(['dfx-mgr-client','-remove'],'current-remove')
    guard(driver,None)
    kernel_check('current-removed',allow_stock_remove=(driver==CFG['stock_srcversion']))
if driver is None:
    # Recover the start failure between original rmmod and candidate insmod.
    # The stopped-daemon absence proof above remains required.
    guard(None,None)
    assert digest('/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko')==CFG['stock_hashes26']['/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko']
    run_logged(['modprobe','zocl','enable_xgq_ert=1'],'initial-missing-driver-stock-modprobe')
    driver=CFG['stock_srcversion']
    guard(driver,None)
    kernel_check('initial-driver-restored')
if override.exists():
    assert digest(override)==CFG['override_text_sha256'],'Foreign or changed drop-in'
    assert [item.name for item in override.parent.iterdir()]==[override.name],'Additional drop-ins exist'
    if pid:
        assert exe==str(candidate),'Drop-in exists but stock/unknown daemon runs'
        run_logged(['systemctl','kill','--kill-who=main','--signal=SIGINT',service],'candidate-sigint')
        run_logged(['systemctl','stop',service],'candidate-stop')
    assert manager_pid()==0
    log=Path(CFG.get('candidate_log',str(WORK/'candidate-manager.log')))
    assert log.is_file() or exe is None,'Running candidate log missing after flush'
    all_errors=[line for line in log.read_text(errors='replace').splitlines() if 'ERROR:' in line] if log.is_file() else []
    write_json(_phase/'candidate-final-log.json',{'path':str(log),'exists':log.is_file(),
        'bytes':log.stat().st_size if log.is_file() else None,
        'sha256':digest(log) if log.is_file() else None,'ERROR_lines':all_errors,'flushed_with':'SIGINT' if exe else None,
        'recovery_continues_despite_candidate_log_errors':True})
    if all_errors:
        recovery_diagnostics.append({'stage':'candidate-final-log','ERROR_lines':all_errors,
                                     'sha256':digest(log),'path':str(log)})
        write_json(_phase/'recovery-diagnostics.json',recovery_diagnostics)
    override.unlink()
    override.parent.rmdir()
    run_logged(['systemctl','daemon-reload'],'daemon-reload')
    run_logged(['systemctl','start',service],'stock-manager-start')
    wait_manager(False)
    manager_guard(False)
else:
    assert exe in [None,'/usr/bin/dfx-mgrd'],'Candidate runs without reviewed drop-in'
    if not pid:
        run_logged(['systemctl','start',service],'stock-manager-start')
        wait_manager(False)
    manager_guard(False)
assert not override.exists() and not override.parent.exists()
driver=mod_version.read_text().strip() if mod_version.exists() else None
current=active_packages()
assert current in [[],[(OFFICIAL_APP,0)]]
if driver==CFG['fixed_srcversion']:
    if current:
        guard(driver,OFFICIAL_APP)
        run_logged(['dfx-mgr-client','-remove'],'stock-autoload-remove')
    guard(driver,None)
    kernel_check('fixed-driver-before-remove')
    run_logged(['rmmod','zocl'],'fixed-driver-rmmod')
    guard(None,None)
    assert digest('/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko')==CFG['stock_hashes26']['/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko']
    run_logged(['modprobe','zocl','enable_xgq_ert=1'],'stock-driver-modprobe')
    guard(CFG['stock_srcversion'],None)
elif driver==CFG['stock_srcversion']:
    guard(driver,OFFICIAL_APP if current else None)
elif driver is None:
    assert not current
    guard(None,None)
    assert digest('/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko')==CFG['stock_hashes26']['/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko']
    run_logged(['modprobe','zocl','enable_xgq_ert=1'],'missing-driver-stock-modprobe')
    guard(CFG['stock_srcversion'],None)
else:
    raise RuntimeError('Unexpected driver during recovery')
if not active_packages():
    guard(CFG['stock_srcversion'],None)
    run_logged(['dfx-mgr-client','-load',OFFICIAL_APP],'official-restore-load')
guard(CFG['stock_srcversion'],OFFICIAL_APP)
manager_guard(False)
kernel_check('official-restored')
query=dpu_query(OFFICIAL_APP,'restored-query',driver=CFG['stock_srcversion'],candidate=False)
output=run_logged([CLASSIFIER,'resnet18',IMAGE],'restored-classification',app=OFFICIAL_APP,
                  cwd='/home/root/kv260-test-20261001',combined=True)
actual=re.findall(r'r[.]index +([0-9]+).*r[.]score +([0-9.eE+-]+)',output)
assert actual==TOP5,'Restored Top-5 differs'
guard(CFG['stock_srcversion'],OFFICIAL_APP)
manager_guard(False)
kernel_check('restored-functional')
hashes={path:digest(path) for path in CFG['stock_hashes26']}
assert hashes==CFG['stock_hashes26'],'Original files or VART not restored'
assert len(hashes)==26
dropins=subprocess.check_output(['systemctl','show',service,'--property=DropInPaths','--value'],text=True).strip()
assert not dropins
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==CFG['boot_id']
finish_phase({'original_baseline_restored':True,'boot_id':CFG['boot_id'],
    'driver':CFG['stock_srcversion'],'active':active_packages(),'original_hashes':hashes,
    'query':query,'top5':actual,'stock_files_overwritten':False,
    'recovery_diagnostics':recovery_diagnostics,'experiment_valid':not recovery_diagnostics},
    passed=not recovery_diagnostics)
