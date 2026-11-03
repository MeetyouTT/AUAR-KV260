"""Build an explicitly untimed preview from actual board GLES2 PNG captures."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image
phase=Path(__file__).parent;base=phase.parent;results=base/'evidence/native_integration/results'
capture=json.loads((results/'final-profile/capture.json').read_text(encoding='utf8'))
source=results/'final-profile/idle-expression'
paths=sorted(source.glob('*.png'));assert len(paths)==135
images=[Image.open(str(path)).convert('RGB') for path in paths]
sheet=Image.new('RGB',(423*3,438))
for i,index in enumerate((0,60,120)):sheet.paste(images[index],(423*i,0))
palette=sheet.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
frames=[frame.quantize(palette=palette,dither=Image.Dither.NONE) for frame in images]
frames[0].save(str(phase/'idle-expression-preview.gif'),save_all=True,append_images=frames[1:],loop=0,
  duration=[(70,70,60)[i%3] for i in range(len(frames))],disposal=2,optimize=False)
images[0].save(str(phase/'native-preview.png'))
counts={}
for folder in (results/'final-profile/scenario',results/'precision'):
    for path in sorted(folder.glob('*.png')):
        if path.stem in ('motion_self','sprite_self','ordinary_child','other_stencil'):continue
        a=np.array(Image.open(str(path)).convert('RGB'))[118:138,235:251]
        counts[path.relative_to(results).as_posix()]=int(np.all(a>=245,axis=2).sum())
face_images={name:Image.open(str(results/'precision'/(name+'.png'))).convert('RGBA').tobytes() for name in ('normal','smile','angry','sad','concern','shy')}
distinct=len({hashlib.sha256(data).hexdigest() for data in face_images.values()})
assert distinct==6
nose_rows=[]
for name in ('normal','smile','angry','sad','concern','shy','pose0','pose1','extreme0','extreme1'):
    reference=(name if name.startswith(('pose','extreme')) else 'face-'+name)+'.png'
    a=np.array(Image.open(str(phase/'native_references'/reference)).convert('RGB'))[118:138,235:251]
    b=np.array(Image.open(str(results/'precision'/(name+'.png'))).convert('RGB'))[118:138,235:251]
    wa=np.all(a>=245,axis=2);wb=np.all(b>=245,axis=2)
    nose_rows.append(dict(case=name,source=int(wa.sum()),native=int(wb.sum()),same_white_positions=bool(np.array_equal(wa,wb)),
      nose_mae=float(np.abs(a.astype('i2')-b.astype('i2')).mean())))
assert all(row['same_white_positions'] for row in nose_rows)
(phase/'nose-source-comparison.json').write_text(json.dumps(dict(static_cases=nose_rows,same_white_pixels_all_cases=True),indent=2),encoding='utf8')
report=dict(purpose='untimed native model visual evidence; no inference of capture FPS',clip_frames=135,clip_duration_seconds=9,
  expressions=[0,1,5],mouth_range=[min(r['mouth'] for r in capture['frames']),max(r['mouth'] for r in capture['frames'])],
  eye_range=[min(r['eye'] for r in capture['frames']),max(r['eye'] for r in capture['frames'])],
  changed_pixels_first_to_last=int(np.any(np.array(images[0])!=np.array(images[-1]),axis=2).sum()),
  six_static_faces_distinct=distinct,
  nose_box=[235,118,251,138],near_white_threshold_rgb=[245,245,245],near_white_counts=counts,
  total_near_white_nose_pixels=sum(counts.values()),source_files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
report['near_white_interpretation']='Raw counts include authored nose highlights; static highlights match the original engine at identical pixel positions in all10 cases.'
(phase/'visual-evidence.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ('source_files','near_white_counts')}))
