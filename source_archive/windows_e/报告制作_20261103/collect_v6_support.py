from pathlib import Path
import subprocess,json,sys,hashlib
sys.stdout.reconfigure(encoding='utf-8')
R=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5\v6_verified_revision')
code=r'''
from pathlib import Path
import json,hashlib,zipfile,struct,ast,math
dest=Path('/home/ghmd/auar-techdoc-01a1a1a5/revision_v6');dest.mkdir(parents=True,exist_ok=True)
root=Path('/home/ghmd/aura-dpu-vision-20261021/work')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records=[]
def read_array(z,name):
 b=z.read(name+'.npy');assert b[:6]==b'\x93NUMPY'
 if b[6]==1:hlen=struct.unpack('<H',b[8:10])[0];start=10
 else:hlen=struct.unpack('<I',b[8:12])[0];start=12
 hdr=ast.literal_eval(b[start:start+hlen].decode('latin1').strip())
 assert not hdr['fortran_order']
 return hdr,b[start+hlen:],b
def npy(shape,dtype,raw):
 h=repr({'descr':dtype,'fortran_order':False,'shape':shape}).encode('ascii')
 h+=b' '*(-(10+len(h)+1)%64)+b'\n'
 return b'\x93NUMPY\x01\x00'+struct.pack('<H',len(h))+h+raw
for kind,expected in [('yunet','f8f57473c90ff9a0ad305883159a0c0d95579f436807c46bc215b9c33473290a'),('sface','aae6d110248d965cb26bdfeea688eba31ff0201291fb8f6703e0e5b32d6f8d93')]:
 p=root/(kind+'-hardware-vectors.npz');assert sha(p)==expected
 with zipfile.ZipFile(p) as z:
  ih,iraw,_=read_array(z,'images_bgr');ishape=ih['shape'];assert ishape[0]==4 and ih['descr']=='|u1'
  image_bytes=math.prod(ishape[1:]);assert len(iraw)==image_bytes*4
  keys_all=[n[:-4] for n in z.namelist() if n.endswith('.npy')]
  cases=[]
  for i in range(4):
   keys=sorted(k for k in keys_all if k.startswith('sample_%d_'%i));outs=[]
   for k in keys:
    h,raw,_=read_array(z,k)
    outs.append({'name':k.split('_',2)[2],'shape':list(h['shape']),'dtype':h['descr'],'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
   cases.append({'sample_index':i,'input_image_bytes':image_bytes,'input_image_sha256':hashlib.sha256(iraw[i*image_bytes:(i+1)*image_bytes]).hexdigest(),'output_elements':sum(math.prod(o['shape']) for o in outs),'outputs':outs,'input_kind':'synthetic_zero' if kind=='yunet' and i==2 else 'synthetic_seed_142' if kind=='yunet' and i==3 else 'public_face_not_redistributed'})
  records.append({'kind':kind,'original_npz_sha256':sha(p),'original_npz_bytes':p.stat().st_size,'cases':cases})
  if kind=='yunet':
   image=iraw[2*image_bytes:3*image_bytes];assert ishape[1:]==(320,320,3) and not any(image)
   vals={'input_bgr_uint8':npy((320,320,3),'|u1',image),'input_nhwc_int8':npy((1,320,320,3),'|i1',bytes(image_bytes))}
   outputs=[]
   for j,k in enumerate(sorted(k for k in keys_all if k.startswith('sample_2_'))):
    h,_,b=read_array(z,k);vals['expected_%d'%j]=b;outputs.append({'key':'expected_%d'%j,'name':k.split('_',2)[2],'shape':list(h['shape'])})
   target=dest/'yunet_zero_vector.npz'
   with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as out:
    for k,b in vals.items():out.writestr(k+'.npy',b)
   meta={'scope':'Synthetic all-zero input and historical expected INT8 outputs extracted from sample 2; no face pixels included; no new inference in this revision','original_npz_sha256':sha(p),'original_sample_index':2,'input_layout':'NHWC','input_fix_point':7,'output_tensors':outputs,'bytes':target.stat().st_size,'sha256':sha(target)}
   (dest/'yunet_zero_vector.json').write_text(json.dumps(meta,indent=2))
(dest/'historical_vector_manifest.json').write_text(json.dumps({'contains_pixels':False,'scope':'Per-case byte counts and hashes only; actual public sample is the synthetic YuNet zero vector','models':records},indent=2))
q=Path('/home/ghmd/auar-scheme-a-9a4f-20261103-01a1a08b/verification/run01/hardware/reports')
report_files=[{'path':str(p),'name':p.name,'bytes':p.stat().st_size} for p in q.iterdir() if p.is_file() and p.suffix in ['.rpt','.json']]
print(json.dumps({'destination':str(dest),'public_vector':meta,'reports':report_files}))
'''
p=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','aura-ubuntu','python3 -'],input=code.encode(),capture_output=True)
if p.returncode:
 print(p.stderr.decode(errors='replace'));raise SystemExit(p.returncode)
info=json.loads(p.stdout)
(R/'evidence/public_vectors').mkdir(exist_ok=True)
for n in ['yunet_zero_vector.npz','yunet_zero_vector.json','historical_vector_manifest.json']:
 subprocess.run(['scp','-o','BatchMode=yes','aura-ubuntu:'+info['destination']+'/'+n,str(R/'evidence/public_vectors'/n)],capture_output=True,check=True)
ex=R/'evidence/implementation';ex.mkdir(exist_ok=True)
src='/home/ghmd/aura-pan-wide-20261028/implementation/drc.rpt'
subprocess.run(['scp','-o','BatchMode=yes','aura-ubuntu:'+src,str(ex/'historical_wide_drc.rpt')],capture_output=True,check=True)
picked=[]
for x in info['reports']:
 if x['name'] in ['implementation.json','timing_summary.rpt','timing.rpt','utilization.rpt','drc.rpt','clocks.rpt','clock_utilization.rpt','route_status.rpt']:
  target=ex/('source_rebuild_'+x['name'])
  subprocess.run(['scp','-o','BatchMode=yes','aura-ubuntu:'+x['path'],str(target)],capture_output=True,check=True)
  picked.append({'path':str(target.relative_to(R)).replace('\\','/'),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
(R/'qa/collected_support.json').write_text(json.dumps({'public_vector':info['public_vector'],'reports':info['reports'],'copied_candidate_reports':picked},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'public_vector':info['public_vector'],'available_reports':[x['name'] for x in info['reports']],'copied_reports':picked},ensure_ascii=False,indent=2))
