from pathlib import Path
import json,shutil,subprocess
root=Path('/home/root/aura-yuki-validation-20261030/native_integration');out=root/'results'
revision='r4_system_visual';seconds=35
for name in ('gtk-clock.json','gtk-clock-samples.json','gtk-final.png'):
    source=out/name;backup=out/(source.stem+'-r1'+source.suffix)
    if source.exists() and not backup.exists():shutil.copyfile(source,backup)
driver=root/('gtk-'+revision+'-worker.py')
driver.write_text(f'''from pathlib import Path
import json,shutil,subprocess,time
root=Path({str(root)!r});out=root/'results';start=time.monotonic()
with (out/'gtk-{revision}.log').open('w') as log:
 result=subprocess.run(['python3',str(root/'host/validate_gtk_clock.py'),{str(seconds)!r}],stdout=log,stderr=subprocess.STDOUT,timeout={seconds+35})
for name in ('gtk-clock.json','gtk-clock-samples.json','gtk-final.png'):
 source=out/name
 if source.exists():shutil.copyfile(source,out/(source.stem+'-{revision}'+source.suffix))
(out/'gtk-{revision}-result.json').write_text(json.dumps(dict(returncode=result.returncode,seconds=time.monotonic()-start)))
''')
with (out/('gtk-'+revision+'-launch.log')).open('w') as log:
    child=subprocess.Popen(['python3',str(driver)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':child.pid,'revision':revision,'seconds':seconds}))
