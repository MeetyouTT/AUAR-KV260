"""Read only the current boot FDT for an exact overlay merge check."""
import base64,hashlib,json
from pathlib import Path
p=Path('/sys/firmware/fdt');raw=p.read_bytes()
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'fdt_sha256':hashlib.sha256(raw).hexdigest(),'fdt_base64':base64.b64encode(raw).decode()}))
