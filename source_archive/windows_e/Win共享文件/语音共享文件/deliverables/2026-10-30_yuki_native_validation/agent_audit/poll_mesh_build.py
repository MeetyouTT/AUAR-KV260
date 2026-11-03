from pathlib import Path
import json
root=Path('/home/root/aura-yuki-validation-20261030/native_integration')
evidence=root/'mesh_evidence'
if (evidence/'execution.json').exists():
 print((evidence/'execution.json').read_text())
if (evidence/'build.log').exists():
 print('\n'.join((evidence/'build.log').read_text(errors='replace').splitlines()[-8:]))
