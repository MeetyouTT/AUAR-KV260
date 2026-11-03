"""Read-only verification of the shadow import alias."""
import hashlib,json
from pathlib import Path
r=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-follow-shadow-live')
a=r/'follow.py';b=r/'shadow_follow.py';ha=hashlib.sha256(a.read_bytes()).hexdigest();hb=hashlib.sha256(b.read_bytes()).hexdigest()
assert ha==hb=='22fa85bed11e4a4ae5ff9db6d747fbeae474f6d871d91a169fd93404e84daf7b'
print(json.dumps({'alias_matches_pinned_shadow_controller':True,'sha256':hb,'bytes':b.stat().st_size}))
