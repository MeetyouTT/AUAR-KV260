"""Independent public source copies, no production/private data operations."""
import hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'voice_entry_name_fix_20261102/candidate_runtime'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SOURCE/'board/runtime/board_speaker_business.py')=='6904267bd016a10a1508b26f372f0db54a71d78eed2eb15b043026218b1b7816'
for mode in ('baseline','candidate'):
 dest=HERE/(mode+'_runtime')
 assert not dest.exists(),'Fresh independent directory required'
 shutil.copytree(SOURCE,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
shutil.copyfile(HERE.parent/'voice_entry_name_fix_20261102/yuki_pair.formal.public.json',HERE/'yuki_pair.formal.public.json')
print('Copied public baseline and candidate runtimes; original sources unchanged')
