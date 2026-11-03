"""Copy actual saved enrollment faces to the PC and make an offline review gallery."""
import base64
import hashlib
import html
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from common.face_features import checked_png

def save_review(payload,base):
    manifest=payload['manifest'];sid=manifest['session_id']
    if not re.fullmatch('[0-9a-f]{32}',sid):raise ValueError('Invalid saved session')
    if manifest.get('image_size')!=[112,112] or manifest.get('contains_full_camera_frames'):
        raise ValueError('Not a face-only archive')
    expected={row['filename']:row['sha256'] for row in manifest['images']}
    selected=manifest.get('selected')
    if selected:expected[selected['filename']]=selected['sha256']
    if set(expected)!=set(payload['files']):raise ValueError('Incomplete saved photo export')
    folder=Path(base)/sid;folder.mkdir(parents=True,exist_ok=True)
    for name,encoded in payload['files'].items():
        if not re.fullmatch(r'(?:frame_[0-9]{10,16}|selected)\.png',name):raise ValueError('Invalid photo filename')
        raw=base64.b64decode(encoded,validate=True);checked_png(raw)
        if hashlib.sha256(raw).hexdigest()!=expected[name]:raise ValueError('Saved image checksum mismatch')
        destination=folder/name
        if destination.is_symlink():raise ValueError('Photo export symlink refused')
        destination.write_bytes(raw)
    (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    labels={'collect':'采集样本','front_selection':'补采正脸','quality_rejected':'质量未通过',
            'pose_rejected':'姿态未通过','validation_pass':'验证合格帧','validation_rejected':'验证未通过'}
    final=set(manifest.get('validation_frame_ids',[]));cards=[]
    for row in manifest['images']:
        fid=row['frame_id'];badges=[labels.get(row['decision'],row['decision'])]
        if selected and fid==selected['frame_id']:badges.append('最终选中模板')
        if fid in final:badges.append('最终独立验证图')
        pose=row['pose'];details='帧 '+str(fid)+' · 清晰度 '+str(round(pose['blur'],1))
        if row.get('score') is not None:details+=' · 相似度 '+format(row['score'],'.3f')
        name=html.escape(row['filename'],quote=True)
        cards.append('<figure><a href="'+name+'"><img src="'+name+'" width="168" height="168" loading="lazy"></a><figcaption><b>'+html.escape(' / '.join(badges))+'</b><br>'+html.escape(details)+'</figcaption></figure>')
    if selected and selected['frame_id'] not in {row['frame_id'] for row in manifest['images']}:
        name=html.escape(selected['filename'],quote=True)
        cards.insert(0,'<figure><a href="'+name+'"><img src="'+name+'" width="168" height="168"></a><figcaption><b>最终选中模板</b><br>帧 '+str(selected['frame_id'])+'；采样图达到上限后单独保留</figcaption></figure>')
    status={'committed':'已正式保存身份','failed':'登记未通过','cancelled':'登记已取消',
            'in_progress':'采样进行中，尚未保存身份','interrupted':'采样中断'}.get(manifest['outcome'],manifest['outcome'])
    warning='<p>本轮达到照片数量上限，部分图片未保存。</p>' if manifest.get('truncated') else ''
    title='身份登记人脸照片'
    page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+title+'</title><style>body{font:16px system-ui;margin:32px;background:#f5f7fa;color:#19212c}main{max-width:1200px;margin:auto}.grid{display:flex;flex-wrap:wrap;gap:16px}figure{margin:0;background:white;padding:12px;border-radius:10px;width:220px}img{display:block;margin:0 auto 12px}figcaption{font-size:13px;line-height:1.7}p{line-height:1.7}</style><main><h1>'+title+'</h1><p>'+html.escape(status)+'；保存 '+str(len(manifest['images']))+' 张人脸采样图。最终模板另存为selected.png，保留当时选中图的原始字节。全部为实际112×112模型输入。点击图片可看原图。</p>'+warning+'<div class="grid">'+''.join(cards)+'</div></main></html>'
    (folder/'照片总览.html').write_text(page,encoding='utf-8')
    validation=[str(folder/row['filename']) for row in manifest['images'] if row['frame_id'] in final]
    report={'status':'SAVED_ENROLLMENT_PHOTOS_EXPORTED','session_id':sid,'outcome':manifest['outcome'],
        'image_count':len(manifest['images']),'selected':str(folder/selected['filename']) if selected else None,
        'validation_images':validation,'gallery':str(folder/'照片总览.html'),'folder':str(folder),
        'all_images_exact_112px_and_hash_verified':True,'names_or_embeddings_exported':False}
    review='# 本次身份登记照片\n\n状态：'+status+'；采样图'+str(len(manifest['images']))+'张。\n\n'
    if report['selected']:review+='## 最终选中模板\n\n![最终模板]('+Path(report['selected']).as_posix()+')\n\n'
    if validation:review+='## 最终独立验证图\n\n'+'\n\n'.join('![验证图'+str(i+1)+']('+Path(path).as_posix()+')' for i,path in enumerate(validation))+'\n\n'
    review+='## 全部采样图\n\n| 照片 | 照片 | 照片 | 照片 |\n| --- | --- | --- | --- |\n'
    cells=[]
    for row in manifest['images']:
        badges=[labels.get(row['decision'],row['decision'])]
        if selected and row['frame_id']==selected['frame_id']:badges.append('最终模板')
        if row['frame_id'] in final:badges.append('最终验证图')
        cells.append('![帧'+str(row['frame_id'])+']('+(folder/row['filename']).as_posix()+')<br>'+' / '.join(badges))
    for offset in range(0,len(cells),4):
        line=cells[offset:offset+4];review+='| '+' | '.join(line+['']*(4-len(line)))+' |\n'
    (folder/'照片预览.md').write_text(review,encoding='utf-8')
    return report

def main():
    sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
    from board_ssh import ssh
    remote=r'''
import base64,hashlib,json,re,urllib.request
from pathlib import Path
h=json.load(urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=4))
a=h['identity'].get('enrollment_photos',{})
if not a.get('enabled') or not a.get('latest_session'):
 print(json.dumps({'status':'NO_ENROLLMENT_PHOTOS_YET','archive':a}));raise SystemExit
root=Path(a['directory']).resolve();sid=a['latest_session'];assert re.fullmatch('[0-9a-f]{32}',sid)
folder=root/sid;assert not folder.is_symlink() and folder.resolve().parent==root
manifest=folder/'manifest.json';assert not manifest.is_symlink() and manifest.stat().st_size<524288
m=json.loads(manifest.read_text());assert m['session_id']==sid and len(m['images'])<=256
entries={r['filename']:r['sha256'] for r in m['images']}
if m.get('selected'):entries[m['selected']['filename']]=m['selected']['sha256']
files={};total=0
for name,sha in entries.items():
 assert re.fullmatch(r'(?:frame_[0-9]{10,16}|selected)\.png',name)
 path=folder/name;assert not path.is_symlink() and path.stat().st_size<=65536
 raw=path.read_bytes();total+=len(raw);assert total<=16777216
 assert hashlib.sha256(raw).hexdigest()==sha;files[name]=base64.b64encode(raw).decode()
print(json.dumps({'manifest':m,'files':files}))
'''
    payload=json.loads(ssh('python3 -B -',remote,timeout=60))
    if payload.get('status')=='NO_ENROLLMENT_PHOTOS_YET':report=payload
    else:report=save_review(payload,ROOT/'身份登记照片')
    (HERE/'latest_photo_export.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
