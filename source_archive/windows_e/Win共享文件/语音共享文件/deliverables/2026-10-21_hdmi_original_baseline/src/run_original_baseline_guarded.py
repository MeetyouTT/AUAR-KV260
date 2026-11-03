"""Reuse the passive boot guard for the original-kernel/USB baseline probe."""
from pathlib import Path

root = Path(__file__).parent
source = (root / 'run_coldboot_readonly.py').read_text()
source = source.replace('board_coldboot_flicker_readonly.py', 'board_hdmi_original_baseline_readonly.py')
source = source.replace('coldboot-flicker-readonly', 'original-baseline-after-manual-power')
source = source.replace("'COLDREAD'", "'ORIGBASE'")
exec(compile(source, str(root / 'run_coldboot_readonly.py'), 'exec'))
