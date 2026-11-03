from pathlib import Path
import hashlib,json,subprocess,sys
R=Path(__file__).resolve().parent;V=Path('/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin');out=R/'validation/rtl';out.mkdir(parents=True,exist_ok=True)
results=json.loads((out/'result.json').read_text()) if (out/'result.json').exists() else []
for name in (sys.argv[1:] or ['tb_wide','tb_servo','tb_pulse_guard','tb_nominal']):
 assert name in ['tb_wide','tb_servo','tb_pulse_guard','tb_nominal']
 work=out/name;work.mkdir(exist_ok=True)
 src=(R/'candidate/tests'/f'{name}.sv').read_text().replace("32'h778d2512","32'h10282601")
 tb=work/f'{name}.sv';tb.write_text(src)
 row={'test':name,'stages':[],'passed':False}
 for args in [[V/'xvlog','-sv',R/'candidate/rtl/visual_servo.sv',tb],[V/'xelab',name,'-s',name,'-debug','typical'],[V/'xsim',name,'-runall']]:
  label=Path(args[0]).name
  with (work/(label+'.log')).open('w') as f:p=subprocess.run([str(x) for x in args],cwd=work,stdout=f,stderr=subprocess.STDOUT,timeout=240)
  text=(work/(label+'.log')).read_text(errors='replace');row['stages'].append({'name':label,'returncode':p.returncode})
  if p.returncode or 'Fatal:' in text or 'ERROR:' in text:break
 else:row['passed']=any(marker in text for marker in ['AURA_WIDE_TEST_PASS','AURA_SERVO_TEST_PASS','AURA_NOMINAL_TEST_PASS','AURA_V2_PULSE_GUARD_OFFLINE_PASS_NOT_BOARD_RELEASE'])
 results=[r for r in results if r['test']!=name]+[row];(out/'result.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(row),flush=True)
 if not row['passed']:raise SystemExit(1)
