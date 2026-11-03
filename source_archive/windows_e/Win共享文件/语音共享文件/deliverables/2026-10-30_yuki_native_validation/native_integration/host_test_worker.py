from pathlib import Path
import hashlib,json,subprocess,time,traceback
root=Path('/home/root/aura-yuki-validation-20261030/native_integration');base=root.parent
out=root/'results';out.mkdir(exist_ok=True)
def ui():return subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','ExecStart'],text=True)
report={'status':'RUNNING','before_ui':ui(),'steps':[],'production_deployed':False}
def run(command,timeout=180):
    started=time.monotonic()
    with (root/'host-test.log').open('a') as log:
        log.write(json.dumps(command)+'\n');log.flush()
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=timeout)
    report['steps'].append({'argv':command,'returncode':result.returncode,'elapsed':time.monotonic()-started})
    (root/'host-test-result.json').write_text(json.dumps(report,indent=2))
    return result.returncode
try:
    assert json.loads((root/'host-build-result.json').read_text())['status']=='PASS'
    # Includes the explicit runtime-audit target and any later diagnostic-only TU.
    if run(['nice','-n','15','cmake','--build',str(root/'build_host'),'--parallel','1'],600):raise RuntimeError('Final host build failed')
    model=base/'inputs/ems/yuk_0.ems.json';resx=base/'inputs/ems/yuk_0.ems.resx.json';resources=base/'inputs/ems'
    run([str(root/'build_host/yuki_runtime_audit'),str(model),str(resx),'--resource-root',str(resources),'--output',str(out/'runtime-audit.json'),'--steps','360'])
    run([str(root/'build_host/yuki_frame_export'),str(model),str(resx),str(base/'probe_build/scenario-validation.json'),str(out/'native-frames.json'),'--resource-root',str(resources)])
    run([str(root/'build_host/yuki_frame_export'),str(model),str(resx),str(base/'probe_build/scenario-static-reference.json'),str(out/'native-static-frames.json'),'--resource-root',str(resources)])
    run(['python3',str(root/'host/validate_native.py'),'diagnostics'])
    # These are separate passes; screenshot readback is excluded from the timed loops.
    run(['python3',str(root/'host/validate_native.py'),'continuous','90'],120)
    run(['python3',str(root/'host/validate_gtk_clock.py'),'90'],125)
    report['status']='PASS' if all(step['returncode']==0 for step in report['steps']) else 'FAIL'
except Exception as error:
    report.update(status='FAIL',error=str(error),traceback=traceback.format_exc())
finally:
    report['after_ui']=ui();report['ui_unchanged']=report['before_ui']==report['after_ui']
    report['binary_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'build_host').glob('*') if p.is_file() and p.name in ('libaura_yuki.so','yuki_frame_export','yuki_runtime_audit')}
    (root/'host-test-result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)
