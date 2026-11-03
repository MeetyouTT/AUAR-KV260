from pathlib import Path
import subprocess,datetime,json,hashlib,shutil,time
out=Path(__file__).resolve().parent
base=Path('/home/ghmd/aura-pan-wide-20261028/candidate')
tools=Path('/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin')
scratch=Path('/home/ghmd/auar-report-amd-01a19c53/simulations')
scratch.mkdir(parents=True,exist_ok=False)
delivery=out/'simulations';delivery.mkdir()
state={'schema':'auar-fresh-xsim-1','stage':'RUNNING','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tool_version':'Vivado XSim 2022.2','board_accessed':False,'production_sources_changed':False,'tests':[]}
def save():
 (out/'SIM_STATUS.json').write_text(json.dumps(state,indent=2)+'\n')
save()
try:
 for name in ['tb_nominal','tb_wide','tb_servo','tb_pulse_guard']:
  work=scratch/name;work.mkdir()
  dest=delivery/name;dest.mkdir()
  rtl=work/'visual_servo.sv';shutil.copy2(base/'rtl/visual_servo.sv',rtl)
  original=(base/'tests'/(name+'.sv')).read_text()
  adapted=original.replace("32'h778d2512","32'h10282601")
  tb=work/(name+'.sv');tb.write_text(adapted)
  row={'name':name,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_rtl_sha256':hashlib.sha256(rtl.read_bytes()).hexdigest(),'original_testbench_sha256':hashlib.sha256((base/'tests'/(name+'.sv')).read_bytes()).hexdigest(),'executed_testbench_sha256':hashlib.sha256(tb.read_bytes()).hexdigest(),'build_id_fixture_replacements':original.count("32'h778d2512"),'stages':[],'passed':False}
  state['tests'].append(row);save()
  wave='open_vcd {actual_wave.vcd}\n'
  for signal in ['pwm','resetn','dut/width','dut/target','dut/active','dut/armed','dut/reason','dut/lease_left']:
   wave+='set obs [get_objects -quiet /'+name+'/'+signal+']\nif {[llength $obs]} {log_vcd $obs; log_wave $obs}\n'
  wave+='run all\nclose_vcd\nquit\n'
  tcl=work/'run_wave.tcl';tcl.write_text(wave)
  commands=[['xvlog','-sv',str(rtl),str(tb)],['xelab',name,'-s',name,'-debug','typical'],['xsim',name,'-tclbatch',str(tcl),'-wdb',str(work/'actual_wave.wdb')]]
  for cmd in commands:
   start=time.monotonic();logpath=work/(cmd[0]+'_console.log')
   with logpath.open('w') as stream:
    p=subprocess.run([str(tools/cmd[0])]+cmd[1:],cwd=work,stdout=stream,stderr=subprocess.STDOUT,timeout=360)
   text=logpath.read_text(errors='replace')
   stage={'name':cmd[0],'returncode':p.returncode,'elapsed_seconds':time.monotonic()-start,'error_marker_present':any(x in text for x in ['ERROR:','FATAL_ERROR:','Fatal:'])}
   row['stages'].append(stage);shutil.copy2(logpath,dest/logpath.name);save()
   if p.returncode or stage['error_marker_present']:break
  else:
   row['passed']=any(m in text for m in ['AURA_WIDE_TEST_PASS','AURA_SERVO_TEST_PASS','AURA_NOMINAL_TEST_PASS','AURA_V2_PULSE_GUARD_OFFLINE_PASS_NOT_BOARD_RELEASE'])
  row['pass_markers']=[line.strip() for line in text.splitlines() if '_PASS' in line]
  row['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
  for p in [rtl,tb,tcl,work/'actual_wave.vcd',work/'actual_wave.wdb']:
   if p.is_file():shutil.copy2(p,dest/p.name)
  save()
  if not row['passed']:
   state['stage']='FAILED';break
 else:state['stage']='ALL_4_PASSED'
except Exception as exc:
 state['stage']='FAILED';state['error']=type(exc).__name__+': '+str(exc)
state['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
