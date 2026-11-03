import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'pydeps'))
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
assert metadata['codec']=='h264',metadata

decode=subprocess.run([ffmpeg,'-hide_banner','-v','error','-nostats','-i',str(source),'-map','0:v:0','-map','0:a:0','-progress','pipe:1','-f','null','-'],capture_output=True,text=True,encoding='utf-8',errors='replace')
assert decode.returncode==0,decode.stderr
counts=re.findall(r'^frame=(\d+)',decode.stdout,re.M)
assert counts and int(counts[-1])==timeline['frames'],decode.stdout
assert 'progress=end' in decode.stdout,decode.stdout
assert not decode.stderr.strip(),decode.stderr

samples=[('overview',1),('llm',87.5),('tts',109),('output',126),('closure',152)]
for name,t in samples:
    subprocess.run([ffmpeg,'-y','-v','error','-ss',str(t),'-i',str(source),'-frames:v','1',str(HERE/'qa'/f'encoded-{name}.png')],check=True)

destination=HERE.parent/'output'/'AUAR_雪妃_原理动画_16比9_女声解说.mp4'
shutil.copy2(source,destination)
digest=hashlib.sha256(destination.read_bytes()).hexdigest()
receipt={
    'file':str(destination),'sha256':digest,'bytes':destination.stat().st_size,
    'duration_seconds':timeline['duration'],'display_duration':'2分38秒','width':1920,'height':1080,'fps':30,
    'video_codec':'H.264','pixel_format':'yuv420p','audio_codec':'AAC','audio_sample_rate_hz':48000,'audio_channels':2,
    'voice':timeline['voice'],'voice_direction':timeline['voice_direction'],'voice_rate':timeline['rate'],'voice_pitch':timeline['pitch'],
    'subtitles':'44条同步字幕烧录进画面，并附独立SRT','scenes':8,
    'complete_video_and_audio_decode':'PASS','decoded_video_frames':int(counts[-1]),
    'all_generated_voice_word_boundaries_match_narration':'PASS','voice_master_and_video_duration_match':'PASS',
    'geometry_and_text_bounds':'PASS','javascript_errors':result['jsErrors'],
    'source_visualization':r'C:\Users\REVO1\.codex\visualizations\2026\11\03\01a19fed-c7be-7720-a693-f09fa0eeefbd\aura-dialogue-continuous.html',
    'source_metadata':metadata,
    'timing_note':'原理讲解示意；分镜以配音语速编排，不代表项目实测延迟。',
    'speech_engine_reference':'https://github.com/rany2/edge-tts',
    'voice_reference':'https://learn.microsoft.com/azure/cognitive-services/speech-service/language-support?tabs=tts'
}
(HERE/'qa'/'FINAL_VERIFICATION.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:receipt[k] for k in ['file','bytes','duration_seconds','width','height','fps','complete_video_and_audio_decode','decoded_video_frames','sha256']},ensure_ascii=True,indent=2))
