from pathlib import Path
import json
from PIL import Image
import numpy as np
BASE=Path(__file__).parent.parent
def read(path):return np.array(Image.open(str(path)).convert('RGB')).astype(np.int16)
results=[]
for name in ('normal','smile','angry','sad','concern','shy'):
    reference=read(BASE/'reference_controlled'/('complete-'+name+'-reference.png'))
    row={'expression':name}
    for mode in ('complete','bp'):
        native=read(BASE/'evidence/native_integration/results'/(mode+'-'+name+'-native.png'))
        delta=np.abs(reference-native)
        row[mode]={'mae':float(delta.mean()),'pixels_over_20':int(np.any(delta>20,axis=2).sum()),'max':int(delta.max())}
    results.append(row)
report={'faces':results,'complete_parameter_count':57,'source_capture_order':'after-core-update-before-draw',
 'reference_format':'lossless PNG','bp_profile_still_diagnostic':True}
(BASE/'native_integration/complete-face-comparison.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))
