import json,subprocess,time
raw=subprocess.check_output(['journalctl','-k','-n','2000','-o','json','--no-pager'],timeout=5).decode()
rows=[json.loads(line) for line in raw.splitlines() if line.strip()]
matches=[row for row in rows if "WARN: HC couldn't access mem fast enough" in row.get('MESSAGE','')]
print(json.dumps({'read_mono':time.monotonic(),'kernel_window_first_mono_us':rows[0].get('__MONOTONIC_TIMESTAMP') if rows else None,'latest_matching_usb_warning_mono_us':matches[-1].get('__MONOTONIC_TIMESTAMP') if matches else None,'scope':'Bounded last 2000 kernel entries; compare coverage to candidate start'}))
