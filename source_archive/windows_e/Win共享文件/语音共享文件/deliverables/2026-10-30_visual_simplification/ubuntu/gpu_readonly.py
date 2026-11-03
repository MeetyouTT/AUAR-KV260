"""Read only admission/health metadata; no model load, unload or inference."""
import json
import urllib.request
with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=5) as response:
    health = json.load(response)
allowed = {key:value for key,value in health.items()
           if key.startswith('gpu') or key in ('ready','busy','service_revision','model')}
print(json.dumps(dict(status='READ_ONLY',health_keys=sorted(health),health=allowed,
                     model_changed=False,model_unloaded=False)))
