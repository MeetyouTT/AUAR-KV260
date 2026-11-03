"""Read live DT and firmware provenance before any source-platform switch."""
import hashlib
import json
from pathlib import Path

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
tree = Path('/sys/firmware/devicetree/base')
nodes = []
for prop in tree.rglob('compatible'):
    values = prop.read_bytes().rstrip(b'\0').split(b'\0')
    if any(v in (b'fpga-region', b'xlnx,zocl') or b'i2s' in v or b'audio-formatter' in v for v in values):
        node = prop.parent
        nodes.append({'path': '/' + str(node.relative_to(tree)),
                      'compatible': [v.decode() for v in values],
                      'properties': {name: (node/name).read_bytes().hex()
                                     for name in ('reg', 'status', 'firmware-name') if (node/name).exists()}})
root = Path('/lib/firmware/xilinx/kv260-benchmark-b4096')
firmware = {p.name: sha(p) for p in root.iterdir() if p.is_file()}
overlays = Path('/sys/kernel/config/device-tree/overlays')
managers = []
for m in Path('/sys/class/fpga_manager').glob('*'):
    managers.append({'path': str(m), 'state': (m/'state').read_text().strip()})
print(json.dumps({'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  'base_fdt_sha256': sha(Path('/sys/firmware/fdt')),
                  'live_nodes': nodes, 'official_firmware_sha256': firmware,
                  'overlay_status': {p.name: (p/'status').read_text().strip() for p in overlays.iterdir() if (p/'status').exists()},
                  'fpga_managers': managers, 'mmio_accessed': False,
                  'fpga_modified': False, 'motion_command_emitted': False}, indent=2))
