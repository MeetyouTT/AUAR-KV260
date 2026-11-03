"""Wait locally for both observers to close, then render numeric data on Ubuntu."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,time,json,sys,hashlib,traceback,math
from PIL import Image,ImageOps,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent.parent
SHARED=Path('E:/Win共享文件/语音共享文件/deliverables/2026-11-02_5090_deployment/joint_acceptance_180s_20261102')

def read(p):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {}
def publish(phase,**fields):
 value={'phase':phase,'updated_utc':datetime.now(timezone.utc).isoformat(),'board_calls_by_finisher':0,**fields}
 p=ROOT/'AUTO_FIGURE_STATUS.json';tmp=p.with_suffix('.json.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(p)

def main():
 publish('WAIT_LOCAL_CLOSED_ACTUAL_WINDOW')
 deadline=time.monotonic()+28800
 while time.monotonic()<deadline:
  resource=read(ROOT/'RESOURCE_OBSERVER_STATUS.json');functional=read(SHARED/'FUNCTIONAL_OBSERVER_STATUS.json')
  if resource.get('collector_active') is False and resource.get('phase')=='COLLECTED_WAIT_MAIN_WINDOW_SAMPLES' and functional.get('phase')=='FINISHED':break
  if resource.get('phase')=='RESOURCE_OBSERVER_ERROR':raise RuntimeError('Resource observer error; preserve data and wait for explicit recovery')
  if functional.get('phase')=='FAILED':raise RuntimeError('Main observation failed; do not label as a complete acceptance window')
  time.sleep(1)
 else:raise RuntimeError('Local wait ended without a closed formal observation window')
 publish('RENDERING_CLOSED_NUMERIC_WINDOW',run_id=resource.get('run_id'))
 with (ROOT/'data'/'auto_render.log').open('wb') as log:
  r=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts'/'render_completed_run.py')],stdout=log,stderr=subprocess.STDOUT,timeout=450,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,'Offline renderer failed; retained auto_render.log'
 summary=read(ROOT/'data'/'RESOURCE_SUMMARY.json');sources=read(ROOT/'FIGURE_SOURCES.json')
 assert summary.get('observer_completed') is True and summary.get('observer_stopped_early') is False
 assert summary.get('camera_owner_change_samples')==0 and summary.get('boot_change_samples')==0
 assert summary.get('plotted_samples',0)>=2
 records=[json.loads(x) for x in (ROOT/'data'/'acceptance_board_numeric.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
 samples=[r for r in records if r.get('event')=='sample']
 times=[r['board_monotonic_s'] for r in samples];assert all(b>a for a,b in zip(times,times[1:]))
 for row in samples:
  cpu=row['cpu'].get('cpu');assert type(cpu) in (int,float) and math.isfinite(cpu) and 0<=cpu<=100
  memory=row['memory_kib'];assert 0<=memory['MemAvailable']<=memory['MemTotal']
 for source in sources['sources']:
  p=ROOT/source['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==source['sha256'],'Copied input hash changed'
 thumbs=[]
 font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
 for item in sorted(sources['figures'],key=lambda x:x['name']):
  p=ROOT/'figures'/(item['name']+'.png')
  with Image.open(p) as image:image.verify()
  with Image.open(p) as image:
   assert image.width>=1500 and image.height>=1000
   tile=Image.new('RGB',(820,580),'white');thumb=ImageOps.contain(image.convert('RGB'),(800,535));tile.paste(thumb,((820-thumb.width)//2,35));ImageDraw.Draw(tile).text((10,4),item['name'],fill='black',font=font);thumbs.append(tile)
 qa=ROOT/'qa';qa.mkdir(exist_ok=True)
 sheet=Image.new('RGB',(1640,580*((len(thumbs)+1)//2)),'#DDDDDD')
 for i,tile in enumerate(thumbs):sheet.paste(tile,((i%2)*820,(i//2)*580))
 sheet.save(qa/'全部图表联系页.png')
 proof={'status':'PASS_NUMERIC_AND_IMAGE_FILE_CHECKS','run_id':summary['run_id'],'source_hashes_checked':len(sources['sources']),'png_files_checked':len(thumbs),'resource_samples':len(samples),'boot_and_camera_change_samples':0,'visual_qa':'PENDING_MANUAL_IMAGE_INSPECTION','no_new_board_calls':True}
 (qa/'NUMERIC_ARTIFACT_QA.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
 status=read(SHARED/'RESOURCE_OBSERVER_STATUS.json');assert status.get('collector_active') is False
 status.update(phase='FIGURES_GENERATED_WAIT_VISUAL_QA',updated_utc=datetime.now(timezone.utc).isoformat(),figures_directory=str(ROOT/'figures'),figure_count=len(thumbs),numeric_artifact_qa=proof,pending_board_stage=None,acceptance_paused_by_main=False)
 for p in [SHARED/'RESOURCE_OBSERVER_STATUS.json',ROOT/'RESOURCE_OBSERVER_STATUS.json']:
  tmp=p.with_suffix('.json.finisher.tmp');tmp.write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(p)
 publish('FIGURES_GENERATED_WAIT_VISUAL_QA',run_id=summary['run_id'],figure_count=len(thumbs),contact_sheet=str(qa/'全部图表联系页.png'))

if __name__=='__main__':
 try:main()
 except Exception as exc:
  publish('AUTO_FIGURE_ERROR',error_type=type(exc).__name__,error=str(exc));traceback.print_exc();raise
