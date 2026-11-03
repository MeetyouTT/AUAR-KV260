EXPECTED='abded1ea95a5208287e66ef4a4f6fc7f0591771a8a3e3bd80737e8b557df96a8'
import gzip,hashlib,json,os
from pathlib import Path
raw=gzip.decompress(Path('/proc/config.gz').read_bytes()).decode()
values={line.split('=',1)[0]:line.split('=',1)[1] for line in raw.splitlines() if line.startswith('CONFIG_') and not line.startswith('CONFIG_CC_VERSION_TEXT=')}
digest=hashlib.sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode()).hexdigest()
print(json.dumps({'release':os.uname().release,'normalized_config_sha256':digest,'expected':EXPECTED,
 'configuration_matches':digest==EXPECTED,'normalization':'OnlyCONFIG_CC_VERSION_TEXTexcluded; all other enabled CONFIG declarations retained',
 'keys':len(values),'byteorder':__import__('sys').byteorder}))
