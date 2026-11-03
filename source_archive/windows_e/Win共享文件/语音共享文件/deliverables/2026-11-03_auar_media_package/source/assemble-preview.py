import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parent.parent
CONFIG=json.loads((ROOT/'source'/'media-config.json').read_text(encoding='utf-8'))
FFMPEG=json.loads((ROOT/'.build'/'runtime.json').read_text(encoding='utf-8'))['ffmpeg']

def run(args):
    subprocess.run([FFMPEG,'-y','-v','error',*map(str,args)],check=True)

def still(filename,duration,output):
    run(['-loop','1','-framerate','30','-i',ROOT/'.build'/'qa'/filename,'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-map','0:v:0','-map','1:a:0','-t',duration,'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-r','30','-c:a','aac','-b:a','192k','-movflags','+faststart',output])

photo=ROOT/'.build'/'photo-placeholder.mp4'
principle_title=ROOT/'.build'/'principle-cover.mp4'
demo=ROOT/'.build'/'demo-placeholder.mp4'
still('cover-01-photo-1080.png',CONFIG['photo_placeholder_seconds'],photo)
still('cover-02-principle-1080.png',CONFIG['principle_cover_seconds'],principle_title)
still('cover-03-demo-1080.png',CONFIG['demo_placeholder_seconds'],demo)
clips=[ROOT/'output'/'video'/'AUAR_片头_字标居中淡出_3秒.mp4',photo,principle_title,ROOT/'assets'/'principle-50s.mp4',demo]
args=[]
for clip in clips:args.extend(['-i',clip])
filters=''.join(f'[{i}:v:0]setpts=PTS-STARTPTS[v{i}];[{i}:a:0]aresample=48000,asetpts=PTS-STARTPTS[a{i}];' for i in range(len(clips)))
filters+=''.join(f'[v{i}][a{i}]' for i in range(len(clips)))+f'concat=n={len(clips)}:v=1:a=1[v][a]'
target=ROOT/'output'/'video'/'AUAR_章节串联样片_占位版.mp4'
run([*args,'-filter_complex',filters,'-map','[v]','-map','[a]','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-r','30','-c:a','aac','-b:a','192k','-ar','48000','-ac','2','-t','58','-movflags','+faststart','-metadata','title=AUAR·雪妃 章节串联样片（素材占位版）',target])
timeline=[{'name':'字标居中淡出','start':0,'end':3},{'name':'实物照片章节与占位','start':3,'end':5},{'name':'原理讲解章节','start':5,'end':6},{'name':'原理讲解（已完成）','start':6,'end':56},{'name':'实机效果章节与占位','start':56,'end':58}]
(ROOT/'.build'/'sample-timeline.json').write_text(json.dumps({'file':str(target),'duration':58,'segments':timeline},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'file':str(target),'duration':58,'principle_duration':50},ensure_ascii=True))
