"""Read-only source audit and contact sheets for the transferred v3 batch."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--batch-root',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    batch=args.batch_root; out=args.out
    out.mkdir(parents=True,exist_ok=True)
    qc=json.loads((batch/'qc/review_20261005_numeric.json').read_text(encoding='utf-8'))
    peaks={r['id']:r['peak_frame'] for r in qc['candidates']}
    records=[]; errors=[]
    for folder in sorted((batch/'raw').iterdir()):
        if not folder.is_dir(): continue
        meta=json.loads((folder/'meta.json').read_text(encoding='utf-8'))
        paths=sorted(folder.glob('*.png'))
        graph=batch/'workflows'/meta['api_graph']
        checks={'count':len(paths)==39==meta['frame_count'],
                'source_status':meta['state']=='ok' and meta['status']=='success',
                'api_sha256':sha(graph)==meta['api_graph_sha256'].lower(),
                'first_sha256':sha(paths[0])==meta['sha256_first'].lower(),
                'last_sha256':sha(paths[-1])==meta['sha256_last'].lower()}
        shapes=[]; hashes=[]
        for p in paths:
            with Image.open(p) as im: shapes.append(im.size)
            hashes.append({'file':p.name,'bytes':p.stat().st_size,'sha256':sha(p)})
        checks['all_dimensions']=set(shapes)=={(864,1536)}
        if not all(checks.values()): errors.append(folder.name)
        # Full frame, face, and hands: identical crops across all compared frames.
        ids=[0,peaks[folder.name],38]
        sheet=Image.new('RGB',(900,1060),'#eeeeee'); draw=ImageDraw.Draw(sheet)
        draw.text((12,6),folder.name,fill='black')
        for j,i in enumerate(ids):
            with Image.open(paths[i]) as src: im=src.convert('RGB')
            x=j*300+6
            draw.text((x,30),'frame %02d'%i,fill='black')
            sheet.paste(im.resize((288,512)),(x,50))
            sheet.paste(im.crop((280,110,580,340)).resize((288,221)),(x,580))
            sheet.paste(im.crop((275,510,585,770)).resize((288,242)),(x,814))
        sheet.save(out/(folder.name+'_review.png'))
        faces=Image.new('RGB',(1176,740),'#eeeeee'); fd=ImageDraw.Draw(faces)
        fd.text((6,4),folder.name+' | all 39 face frames',fill='black')
        for i,p in enumerate(paths):
            with Image.open(p) as im: crop=im.convert('RGB').crop((280,110,580,340)).resize((144,110))
            x=(i%8)*147; y=28+(i//8)*142
            fd.text((x,y),'%02d'%i,fill='black'); faces.paste(crop,(x,y+18))
        faces.save(out/(folder.name+'_faces.png'))
        records.append({'id':folder.name,'checks':checks,'reference_name_in_graph':json.loads(graph.read_text(encoding='utf-8'))['5']['inputs']['image'],
                        'review_frames':ids,'pngs':hashes})
    report={'batch':str(batch),'candidates':len(records),'png_frames':sum(len(r['pngs']) for r in records),
            'integrity_errors':errors,'records':records,
            'note':'These are source-integrity checks and review images, not visual acceptance.'}
    (out/'integrity.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'candidates':len(records),'frames':report['png_frames'],'errors':errors}))
    return bool(errors)

if __name__=='__main__': raise SystemExit(main())
