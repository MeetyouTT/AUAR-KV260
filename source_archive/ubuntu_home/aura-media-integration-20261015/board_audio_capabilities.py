"""Inspect MCP01 descriptors and mixer state; do not start recording."""
import json
from pathlib import Path
import subprocess

streams = {}
for card in Path('/proc/asound').glob('card[0-9]*'):
    identity = card / 'id'
    if identity.is_file() and identity.read_text().strip() == 'MCP01':
        streams[str(card)] = {p.name: p.read_text() for p in card.glob('stream*')}
p = subprocess.run(['amixer', '-c', 'MCP01', 'contents'],
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=5)
print(json.dumps({'streams': streams, 'mixer': p.stdout, 'mixer_exit_code': p.returncode}))
