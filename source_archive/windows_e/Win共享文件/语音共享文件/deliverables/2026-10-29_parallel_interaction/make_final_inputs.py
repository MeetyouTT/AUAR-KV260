"""Separate unseen public questions; no microphone or audible playback."""
from pathlib import Path
H=Path(__file__).resolve().parent
source=(H/'make_public_inputs.py').read_text(encoding='utf-8')
start=source.index('spec=[');end=source.index('\nrows=[]',start)
source=source[:start]+'''spec=[('short','请给第一次学习折纸的朋友一句鼓励，带上纸船这个词。'),
 ('medium','请用两句话描写纸船沿着小溪漂流的情景。'),
 ('long','请讲一段八十字左右的小故事，一只小熊在秋天帮松鼠找回了蓝色的雨伞。')]'''+source[end:]
source=source.replace("'public_gpu_'+label+'.wav'","'final_public_'+label+'.wav'").replace("H/'public_inputs.json'","H/'final_public_inputs.json'")
exec(compile(source,str(H/'make_final_inputs.py'),'exec'),dict(__file__=str(H/'make_final_inputs.py'),__name__='__main__'))
