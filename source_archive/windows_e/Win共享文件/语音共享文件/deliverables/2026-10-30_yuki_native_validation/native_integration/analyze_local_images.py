from pathlib import Path
from collections import Counter
import json
from PIL import Image,ImageChops
BASE=Path(__file__).parent.parent
a=Image.open(str(BASE/'native_integration/mask_fixtures/sprite-self-reference-lossless.png')).convert('RGB')
b=Image.open(str(BASE/'evidence/native_integration/results/sprite_self-native.png')).convert('RGB')
diff=ImageChops.difference(a,b);counts=Counter(zip(a.getdata(),b.getdata()))
print(json.dumps({'reference_size':a.size,'native_size':b.size,'diff_bbox':diff.getbbox(),
 'most_common_different_pairs':[(x,y,n) for (x,y),n in counts.most_common() if x!=y][:15],
 'ref_colors':a.getcolors(a.width*a.height)[:10] if len(a.getcolors(a.width*a.height))<10 else Counter(a.getdata()).most_common(6),
 'native_colors':Counter(b.getdata()).most_common(6)},ensure_ascii=True))
