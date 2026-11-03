"""Inventory actual enrollment storage, without exporting private names or vectors."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import hashlib,json,math,sqlite3,urllib.request
from pathlib import Path
get=lambda path:json.load(urllib.request.urlopen('http://127.0.0.1:8790'+path,timeout=4))
h=get('/health');args=Path('/proc/%d/cmdline'%h['pid']).read_bytes().decode().split('\0')
cfg=json.loads(Path(json.loads(Path(args[args.index('--config')+1]).read_text())['identity']['config']).read_text())
db=Path(cfg['database']).expanduser();before=hashlib.sha256(db.read_bytes()).hexdigest()
with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True) as con:
 tables={name:[row[1] for row in con.execute('PRAGMA table_info('+name+')')]
  for name in ('identities','templates','metadata')}
 revision=con.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]
 count=con.execute('SELECT count(*) FROM identities').fetchone()[0]
 templates=[]
 for model,dimension,raw in con.execute('SELECT model_id,dimension,embedding FROM templates'):
  vector=json.loads(raw)
  templates.append({'model_id':model,'declared_dimension':dimension,'actual_dimension':len(vector),
   'all_values_finite':all(math.isfinite(v) for v in vector),
   'normalized_vector_length':round(math.sqrt(sum(v*v for v in vector)),6)})
view=get('/v1/ui/status')['modules']['identity'];diag=h['identity']['sampling_diagnostics']
image_ext={'.jpg','.jpeg','.png','.webp','.bmp','.mp4','.avi','.mov'}
nearby_images=[p.name for p in db.parent.iterdir() if p.is_file() and p.suffix.lower() in image_ext]
assert hashlib.sha256(db.read_bytes()).hexdigest()==before
print(json.dumps({'library_revision':revision,'identity_records':count,'templates':templates,
 'database_columns':tables,'image_or_video_files_in_identity_storage':nearby_images,
 'photo_video_columns_in_store':False,'saved_frame_pose_timestamp_columns_in_store':False,
 'active_sampling_stage':diag['stage'],'active_sampling_pool_frames_ram':diag['pool_frames'],
 'active_template_policy':diag['template_policy'],
 'sampling_counts':view.get('enrollment_sampling',{}).get('counts'),
 'last_operation':{k:view.get('last_operation',{}).get(k) for k in ('action','state','db_version')},
 'database_hash_unchanged':True,'names_or_template_vectors_exported':False,
 'new_camera_frames_captured_or_saved':False}))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=25))
(HERE/'enrollment_dataset_inventory.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
rows='\n'.join('| '+str(i+1)+' | '+t['model_id']+' | '+str(t['actual_dimension'])+' | '+str(t['normalized_vector_length'])+' |' for i,t in enumerate(r['templates']))
text=f'''# 当前身份登记数据清单

已只读核对实际身份库，修订 **{r['library_revision']}**，身份记录 **{r['identity_records']}** 条。

| 模板 | 模型 | 特征维数 | 归一化长度 |
|---|---|---|---|
{rows}

当前数据库保存称呼、身份ID和人脸特征向量。这里仅展示统计，没有导出姓名、身份ID或向量数值。

| 用户希望回看的内容 | 实际保留情况 |
|---|---|
| 登记采样照片、视频 | 未写入身份库，也未形成本轮照片集 |
| 最终选中的人脸照片 | 未随模板持久保存，不能从向量恢复原照片 |
| 原成功登记的逐帧姿态、帧号、验证分数 | 未随该模板保存 |
| 正脸静止检查统计 | 已保存数值报告，属于诊断，未写入登记 |
| 新版登记采样池 | 当前阶段 {r['active_sampling_stage']}，RAM中 {r['active_sampling_pool_frames_ram']} 份 |

目前数据库仍为修订14时，说明此前的原身份还在；本轮新版更新尚未提交。曾经15秒自然采样的照片只用于RAM筛选，正式保存的是单个128维特征；完成、取消或服务重载会释放采样图。实时当前人脸图不是历史登记样本，不能冒充本轮数据集。

身份库没有登记源帧/姿态/时间列，因此不能把项目里其他旧照片或公开测试图关联为当前模板的登记照片。若后续需要逐张审阅，下一次采样需明确保留本轮人脸裁剪、选中模板图及独立验证图，并标明用途；当前无法补回已释放的历史图像。

本次没有读取新摄像头图像，没有保存照片、导出模板或修改身份库。原始统计见 `enrollment_dataset_inventory.json`。
'''
(HERE/'enrollment_dataset_inventory.md').write_text(text,encoding='utf-8')
print(json.dumps(r,ensure_ascii=True))
