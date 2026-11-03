PAYLOAD='H4sIAAAAAAAC/61W32/iOBB+56+I+uJkN5gfpe0KlIdqS3touYIolU5CyDKJAR9JHNkOLar6v9/YiVnoVrsvl4cknhl/M/PNeJKLi4t7/soSj+6pptLTPGNq4OXCe5j/aNEy4aIV04xJ2spEwlJPlrm18YT0CimSMtZc5N6L5JopfHFx0eBZIaT24qkUa54yt95StU35yi25cG//KpG7d6Eaaykyr6DaGHu1eApLZ1IoTbVyK8mUKGV89GKUXGkeHy3U4fhqAm80ZpPJPDKIPmptRcZaUggNqUraTIqyuecKEmp2293rTrvbaRVC6UK8MNmUTMtDM+V72MJSRhUDUcrpiqdcH5rrm+tu7+aq1778tm72rtqdy+vWpuTNmjEUNCAUnIhcE8sWWR00i4HUaC5LZpUmbcxzxaT226HS0jfBtpAJDgVBxY0WIgUclgmiYskL7ViKJaMAazWxkADJqIy3UQqE+A4+aBhV9NHWR5KVCoIcOMNFfxlVAKduc6B3z0gBPZMq5/jRCqdWdmoMPlKTOlnTmNOf9rNafl+JG40KLjrFOcm8ZdFa0A9mVfvGSqBQb8FFoqLLoIbAscjXfFNCQiarYFB7jj64rLQNyUw80RtSsSgY6qPR02R8Ox/ekfvRP3Cfj/4ekim8jsl0NrkfjYfkcTI373fP3+ejySOZ/zUb3t6R79NnFDa8+kKu5H1XwiBENXN1yKh/CSJB7Akj1Qkj9oSRFyF3qG96IkSmnRkYL5bvDWi+vnWxhqNnFR7PPR+N7sZDFKKn6fD2x+jxgTwOn+ez2zEK+seATLZQDcU0KVJ6WNF45x+5wSuRHCqtHxy3GCc8T9ircSJpvmF+7wTRXDqyBl9wp3v1Fbc7nUHGNI2ss4Qr44msJaTm22hDHZxtd+5pUaQH32wNdYi/eXxdZYfhLrV64eakuuxQ4EGZmdfGIb75ifdC0zRaLAdxUZoH7NwwBXU1sVQxGA5DVPusCHWbi2pQRW5i4foJFNUqzHK6MoLf0dP9lR/fmnztBSccrdiG5pFpD5yJXGiR8xg8weFLKin4jJlSxCz8c8r+xO8g48kv0GcIPANmov+B+gWyUGh5Bs/yP/g3hTJuwdD34da0dARfOu12OzDlOyo/4aJpSKptz1Crei9Oy708AgEn516ctWuG5VlAYP7RhesCIL1qA4CAU5xFXOAnLXm+GU1Ms9gvE0jg7td7wtqyegQwtaQm1s5HcZlVHwZIk+dO3D1xXM2nhRsDx0DfKomZL6bwyKYMXd3thcgwTIqrNslUpa8+hzhjCae5b9RBeMYeAtp/swO0QQ2b0VdrBM9PgSyzR6i33Sdo+8CenV24NyenKgWGr2Gm/OD9A1w9MlOqNDExWmvUd6MeJPZXxIfwarrtxAWi8YbpPU1LqNUHTAtmW5eoLe1eXaN+/WeCq7VvlVgL83kG7ABv2WvCIUwYj+9VbVxdCkZ3REJ/7vgKLSP3M2K8y1IBjH8UzZ6fbh+G5Gk4vg+wLA2VsLGx5jnwWA92l1gqlDn5tit883uEkzIrlF+5hf+A/wBwYpcitgkAAA=='
SOURCE_SHA='3721047acaef0939c2b5bcfb37fd646748ba390d12d73bd60b6cea9731f20509'
import base64,gzip,hashlib,json,subprocess,os,sys
from pathlib import Path
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()=='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
raw=gzip.decompress(base64.b64decode(PAYLOAD));assert hashlib.sha256(raw).hexdigest()==SOURCE_SHA
root=Path('/home/root/aura-gui-cpu-20261023')/SOURCE_SHA[:16];root.mkdir(parents=True,exist_ok=True,mode=0o700)
p=root/'profile.py'
if p.exists():assert p.read_bytes()==raw
else:p.write_bytes(raw)
assert not (root/'done.json').exists(),'Do not overwrite a profile'
runner="import json,subprocess,sys;from pathlib import Path;p=Path(sys.argv[1]);r=subprocess.run(['/usr/bin/python3','-B',str(p/'profile.py')],capture_output=True,text=True,timeout=70);(p/'stdout.json').write_text(r.stdout);(p/'stderr.log').write_text(r.stderr);(p/'done.json').write_text(json.dumps({'exit_code':r.returncode}))"
unit='aura-gui-profile-'+SOURCE_SHA[:16]
r=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=90','--property=Nice=10','/usr/bin/python3','-B','-c',runner,str(root)],capture_output=True,text=True,timeout=8)
assert r.returncode==0,r.stderr
print(json.dumps({'started':True,'root':str(root),'unit':unit,'source_sha256':SOURCE_SHA}))
