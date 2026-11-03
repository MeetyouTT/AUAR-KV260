DATA='H4sIAAAAAAAC/6VWS4/bNhC++1cIuVBCbFm2vH4tdGjSpMihSdGkJ8MQxuJozUYSVZLaXTfIf++QlO31xgkCVAfZGo6+eX+j1x/ev333W/aFQWHEPRghm1xhK5Vh64CN97LGsZLSjKFTMFJYIWgcQVFga6ApcDRNpvNJMk3H85TPprMZnwPnKfBk7GHiv7Vs2DBge2i4LMvcol3DLqRUXDRgkI/0gzDF/oytsJD3qA43yWiyWiwXyVNAvYfpzdxCTqYwhxnCalmm6Wo6n81veIpJsZsDJrN5UaawnJbTVbkDWCbTCZ/tEIBPZ6tyVSzSmUVVsqp2UHzOWzD7/5+DHi1uDxfgZ5/LZJamyxmf8OXNapHAApe42E3LRTIp4GaRzicLDpNksZghqUICMMFlskrnME13u2XBvg5evHjxK5bQVSYQOlAIfCSb6hCIRrdY2JLGwYj81kYqDEDVOoCGTjm2SLfGBPKhQR6cnCXAgaht9YI96H0ldkP/SP/izohqaIs6lHqoD3pQKlkHNlt0GvSv/UGPg8GAYxn0dnNnI5StHl6kOFoPArpIHlOFRXkIIycQpZPZaA4hk0rcUW9ULForNJ1qgi+sBa2Rs/Un1eGQQeVU85NmL7/rQPG8wtLkFLnVfwuVxq8nqxZFmVzwinxUOTnbtuSo98KIGlXGXOFraDqoRi6OYzZH7KU2KpQ6vkPTCnotOgHXaGDj7bNt5pBurVzDPeb2MHyiGxeyJgM83DDKqcGaTHQ0N2w06hphMvbSAdhn2YzcsGI2u0m0U2mVbCmIQ/Zn11i93+HxIxZZmtCgOBv2YuNOq/FONOP2YPaySe2rr9jQBnBZku3QgsjOZJPkajx9KreZzfHVoIw6rE+WKVnUnJmvp8tbGN36vPdnG9YfECg1J79e+xOgPeVCkxdh9MTK1cY4Af+4IZwiecLW/tc3CD7aIQ/euB8apAC0la2/b7QHQ6WkYmtzaDGkF6I4zxuoMc9f2qF3TWPFm/UsSbbXnHriLMHY2n/tB6oG0YSFbEpx1w8PzQo1TVxWcKdjSY7W4l9cKxAag74j3lh/QvaLSzoFYnnin07YvPgMWgAuG5M/KGEw3x0McS5HV+GBj9ROdmYnP64kcB3aIe8d2VzZH9vIVTA3+GiOc3EqutXYMGr6tkKDfdGPYk+tp144ivsUb68hXWyXbZYd3bqU+0Dob3bh+6VSdFtL3lWYOc4/HloGf2q4J8bYM3noX/EB29xpijje4yMXd9R/YfStR/0KOPrk5+/Sr8tdtI1+YP/E3T/hwfMt5F2wuyK7pPnYynLL73kpiB4rWbgKh8yzee4pMe9HjA19Fryf9XMwf+jhLHBob9GtvbuGQhXjI9nzemF9Yp6sjl9JmoMPrQ5tTaLba9vCNjCou/vNZE3137DTxmPb9T1UHdXzu5vIgyBN7nmy+zw/haWdGYSb7dCCF3ssPh9rYi9v41v2oXLYbXwU7Nznz5lP3TMxQEHsoCCnHeJP7TLxe8efjDoRk0P3okAWnUndEXvRKUVrPLeb4vRp8axB/Jb56/27T99vkWewR+K9xD277sTWDGq23Zx5evsMp/9i+kmYguZDcLCkQFu940JeSwoQ14C6SIpn7FaJxoSOpXhXU8e4ukSnNmmk8aU680nPlB/d3n3zKEw4iYhrSflI2lnG8tzybp6ztePf1+67ORr8B+LjSDBACwAA'
SHA='e512d80518dda62a0df06af1f79429f814cc52aa40e0c9c2686de89bb4036906'
REPORT='/home/root/aura-release-acceptance-20261023/63d4244d6add3ad0/report.json'
import base64,gzip,hashlib,json,subprocess
from pathlib import Path
report=json.loads(Path(REPORT).read_text());assert report['complete'] and report['passed'] and report['accepted']
release=Path(report['release']);assert release.resolve()==release
assert release.parent==Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live')
p=release/'restore_original.py';assert not p.is_symlink()
raw=gzip.decompress(base64.b64decode(DATA));assert hashlib.sha256(raw).hexdigest()==SHA
if p.exists():assert p.read_bytes()==raw
else:
 with p.open('xb') as f:f.write(raw)
p.chmod(0o600)
r=subprocess.run(['/usr/bin/python3','-B',str(p),'--check'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15)
assert r.returncode==0,r.stderr[-600:]
check=json.loads(r.stdout);assert check['passed'] and check['read_only']
print(json.dumps({'installed':str(p),'sha256':SHA,'read_only_check':check}))
