"""Copy the old independent RAM contract, changing only its runtime location."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
old=HERE.parent/'split_commands_20261102/independent_voice_review/test_original_voice_contract.py'
text=old.read_text(encoding='utf-8')
needle="RUNTIME=LIVE/'start_sync_fix/candidate_runtime'"
assert text.count(needle)==1
text=text.replace(needle,"RUNTIME=HERE/'candidate_runtime'")
(HERE/'test_original_voice_contract.py').write_text(text,encoding='utf-8')
print('Original 24 contract assertions unchanged; only runtime location changed')
