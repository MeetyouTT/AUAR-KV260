"""Read the temporary test's own log; no production process changes."""
import json,subprocess
v=subprocess.run(['journalctl','-b','-u','aura-hdmi-static-test-975f931a.service','-o','cat','--no-pager','-n','18'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
print(json.dumps({'rc':v.returncode,'test_log':v.stdout[-6000:]}))
