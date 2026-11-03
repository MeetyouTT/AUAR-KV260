"""Boot the preserved original kernel after the failed cold-start trial."""
import importlib.util
from pathlib import Path

PREFLIGHT='''import hashlib,json,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='e93b105e-cec2-43af-891f-ef17b0a5be63'
assert hashlib.sha256(Path('/boot/uEnv.txt').read_bytes()).hexdigest()=='05cd73695dc8797899ee32a02ba5081403f02d5b28b8b89b3b71ffe503279ffe'
assert hashlib.sha256(Path('/boot/Image').read_bytes()).hexdigest()=='b02771b1c6ceca7f07b56a97ab36d79d2f17652c58f9c119ddd1d2ea0e554e71'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 with op.open('http://127.0.0.1:8783/api/state',timeout=2) as r:s=json.load(r)
except urllib.error.URLError:s=None
assert s is None or (s['phase']=='IDLE' and not s.get('playing')), 'An active turn must finish first'
print(json.dumps({'original_kernel_and_selection_verified':True,'gui_available':s is not None}))
'''


def main():
    p=Path(__file__).with_name('warmboot_once.py')
    spec=importlib.util.spec_from_file_location('hdmi_original_boot',str(p))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.PREFLIGHT=PREFLIGHT
    m.CAPTURE_SUFFIX='hdmi-original-kernel-restore'
    m.STATUS_FILE='original-kernel-restore.json'
    m.OPERATION='restore_original_kernel_after_failed_coldboot'
    m.main()


if __name__=='__main__':main()
