from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'revision3_natural_lower_arm/preview_r3.py').read_text(encoding='utf8')
prefix=source.split('def percentile(')[0]
target=HERE/'egl_preview.py'
if target.exists():assert target.read_text(encoding='utf8')==prefix
else:target.write_text(prefix,encoding='utf8')
print('R4 EGL helper prepared from the previously verified pbuffer owner')
