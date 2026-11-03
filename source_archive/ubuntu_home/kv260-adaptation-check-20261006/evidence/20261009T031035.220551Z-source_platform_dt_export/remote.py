"""Export current boot's immutable base FDT for host-only overlay validation."""
import base64
import gzip
import hashlib
import json
from pathlib import Path

data = Path('/sys/firmware/fdt').read_bytes()
print(json.dumps({'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  'sha256': hashlib.sha256(data).hexdigest(),
                  'bytes': len(data), 'gzip_base64': base64.b64encode(gzip.compress(data)).decode(),
                  'fpga_modified': False, 'motion_command_emitted': False}))
