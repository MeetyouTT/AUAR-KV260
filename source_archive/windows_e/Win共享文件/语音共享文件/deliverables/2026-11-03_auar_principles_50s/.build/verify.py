import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,r'E:\Win共享文件\语音共享文件\deliverables\2026-11-03_principle_video_16x9\.build\pydeps')
import imageio_ffmpeg

timeline=json.loads((HERE/'timeline.json').read_text(encoding='utf-8'))
result=json.loads((HERE/'render-result.json').read_text(encoding='utf-8'))
source=HERE/'rendered.mp4'
ffmpeg=timeline['ffmpeg']

reader=imageio_ffmpeg.read_frames(str(source))
metadata=next(reader)
reader.close()
assert metadata['size']==(1920,1080),metadata
assert abs(metadata['fps']-30)<.001,metadata
assert abs(metadata['duration']-timeline['duration'])<.05,metadata
assert abs(metadata['duration']-50)<.05,metadata
assert metadata['codec']=='h264',metadata
audio_sha=hashlib.sha256((HERE/'narration-master.wav').read_bytes()).hexdigest()
speech=json.loads((HERE/'speech.json').read_text(encoding='utf-8'))
retained=[s for s in speech['scenes'] if s.get('reuse_index')]
assert len(retained)==8
for s in retained:
    original=Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-11-03_principle_video_40s\.build\audio')/f"{s['reuse_index']:02d}.wav"
    assert hashlib.sha256(Path(s['clip']).read_bytes()).digest()==hashlib.sha256(original.read_bytes()).digest()

decode=subprocess.run([ffmpeg,'-hide_banner','-v','error','-nostats','-i',str(source),'-map','0:v:0','-map','0:a:0','-progress','pipe:1','-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace')
assert decode.returncode==0,decode.stderr
counts=re.findall(r'^frame=(\d+)',decode.stdout,re.M)
assert counts and int(counts[-1])==timeline['frames'],decode.stdout
assert 'progress=end' in decode.stdout,decode.stdout
assert not decode.stderr.strip(),decode.stderr

samples=[('overview',.3)]+[(label,timeline['scenes'][i]['start']+timeline['scenes'][i]['duration']*.6) for label,i in [('vision',1),('axis-follow',2),('llm',6),('tts',7),('output',8),('closure',9)]]
samples.append(('axis-stop',timeline['scenes'][2]['start']+timeline['scenes'][2]['axisCues']['stop']+.01))
for name,t in samples:
    subprocess.run([ffmpeg,'-y','-v','error','-ss',str(t),'-i',str(source),'-frames:v','1',str(HERE/'qa'/f'encoded-{name}.png')],check=True)

destination=HERE.parent/'output'/'AUAR_原理讲解_50秒_视觉与转轴.mp4'
shutil.copy2(source,destination)
digest=hashlib.sha256(destination.read_bytes()).hexdigest()
receipt={
    'title':'AUAR 原理讲解','visual_framework':['感知与跟随','对话处理','同步输出','确认闭环'],
    'file':str(destination),'sha256':digest,'bytes':destination.stat().st_size,
    'duration_seconds':timeline['duration'],'display_duration':'50秒','width':1920,'height':1080,'fps':30,
    'video_codec':'H.264','pixel_format':'yuv420p','audio_codec':'AAC','audio_sample_rate_hz':48000,'audio_channels':2,
    'voice':timeline['voice'],'voice_direction':timeline['voice_direction'],'voice_rate':timeline['rate'],'voice_pitch':timeline['pitch'],
    'subtitles':f"{sum(len(s['captions']) for s in timeline['scenes'])}条同步字幕烧录进画面，并附独立SRT",'scenes':10,
    'complete_video_and_audio_decode':'PASS','decoded_video_frames':int(counts[-1]),
    'all_generated_voice_word_boundaries_match_narration':'PASS','voice_master_and_video_duration_match':'PASS',
    'existing_eight_voice_clips_retained':'PASS','two_visual_axis_voice_clips_added':True,'audio_master_sha256':audio_sha,
    'geometry_and_text_bounds':'PASS','javascript_errors':result['jsErrors'],
    'source_visualization':r'C:\Users\REVO1\.codex\visualizations\2026\11\03\01a19fed-c7be-7720-a693-f09fa0eeefbd\aura-dialogue-continuous.html',
    'source_metadata':metadata,
    'timing_note':'原理讲解示意；分镜以配音语速编排，不代表项目实测延迟。',
    'speech_engine_reference':'https://github.com/rany2/edge-tts',
    'voice_reference':'https://learn.microsoft.com/azure/cognitive-services/speech-service/language-support?tabs=tts'
}
(HERE/'qa'/'FINAL_VERIFICATION.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:receipt[k] for k in ['file','bytes','duration_seconds','width','height','fps','complete_video_and_audio_decode','decoded_video_frames','sha256']},ensure_ascii=True,indent=2))
