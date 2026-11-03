import hashlib,json,runpy,sys
from pathlib import Path
boot='3336afd3-7926-40b3-b5fd-e17b86256830'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
source=Path('/home/root/aura-post-power-20261022/helpers/94c54706b323e41d/source.py')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='94c54706b323e41d415db38395e2ee19bf0bbab98185de523331e072c73b954e'
sys.argv=[str(source),'switch'];runpy.run_path(str(source),run_name='__main__')
