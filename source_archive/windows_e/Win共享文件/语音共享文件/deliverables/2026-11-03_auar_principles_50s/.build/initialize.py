import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
old=json.loads(Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-11-03_principle_video_40s\.build\narration.json').read_text(encoding='utf-8'))
for i,s in enumerate(old['scenes']):
    s['base_phase']=i
    s['reuse_index']=i+1
old['scenes'][1:1]=[
    {
        'title':'视觉感知｜检测图像，跟踪目标位置','short':'视觉','kind':'vision','base_phase':0,
        'text':'相机图像经加速单元检测，处理器持续跟踪目标位置。',
        'captions':['相机图像经加速单元检测，','处理器持续跟踪目标位置。']
    },
    {
        'title':'转轴协同｜偏离时跟随，到位后停止','short':'转轴','kind':'axis','base_phase':0,
        'text':'目标偏离时，板端输出控制脉冲，驱动转轴跟随，到位后停止。',
        'captions':['目标偏离时，板端输出控制脉冲，','驱动转轴跟随，到位后停止。']
    }
]
(HERE/'narration.json').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
print('10 scenes prepared; 8 existing voice clips retained; 2 new explanations added.')
