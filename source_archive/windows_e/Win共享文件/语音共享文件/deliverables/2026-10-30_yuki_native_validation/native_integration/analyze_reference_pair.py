from pathlib import Path
import json
from PIL import Image
import numpy as np
BASE=Path(__file__).parent.parent
def read(path):return np.array(Image.open(str(path)).convert('RGB')).astype(np.int16)
def compare(a,b):
    aa=read(a);bb=read(b);delta=np.abs(aa-bb)
    return dict(mae=float(delta.mean()),max_channel_error=int(delta.max()),different_pixels=int(np.any(delta>0,axis=2).sum()),
      pixels_over_2=int(np.any(delta>2,axis=2).sum()),pixels_over_20=int(np.any(delta>20,axis=2).sum()))
ref=BASE/'reference_controlled';native=BASE/'evidence/native_integration/results'
result={'original_vs_rebuilt_combo':compare(ref/'normal-reference-lossless.png',ref/'rebuilt-combo-reference-lossless.png'),
 'original_engine_combo_vs_removed':compare(ref/'rebuilt-combo-reference-lossless.png',ref/'rebuilt-no-combo-reference-lossless.png'),
 'native_vs_original_normal':compare(ref/'normal-reference-lossless.png',native/'controlled-normal-native.png'),
 'reference_format':'PNG exported by the visible local reference UI; lossless, explicit background',
 'previous_JPEG_screenshots_rejected_for_pixel_thresholds':True}

for tick in ('tick1','tick60'):
 result['combo_vs_removed_'+tick]=compare(ref/('rebuilt-combo-'+tick+'-lossless.png'),ref/('rebuilt-no-combo-'+tick+'-lossless.png'))

result['complete57_native_vs_original']=compare(ref/'complete-normal-reference.png',native/'complete-normal-native.png')
for pose in (0,1):
 result['source_combo_vs_removed_pose'+str(pose)]=compare(ref/('probe-combo-pose'+str(pose)+'-lossless.png'),ref/('probe-no-combo-pose'+str(pose)+'-lossless.png'))
 result['source_manual_extremes_combo_vs_removed_pose'+str(pose)]=compare(ref/('manual-probe-combo-pose'+str(pose)+'-lossless.png'),ref/('manual-probe-no-combo-pose'+str(pose)+'-lossless.png'))
(BASE/'native_integration/reference-pair-comparison.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
