from common import *
from PIL import Image,ImageDraw,ImageFont
import cv2,numpy as np
LABELS=[(0,2,'待机'),(2,3,'唤醒'),(3,6,'聆听'),(6,9,'思考'),(9,12,'普通回答'),(12,13,'点头确认'),
        (13,16,'积极回答'),(16,17,'摇头否定'),(17,20,'低落回答'),(20,21,'困惑'),(21,23,'继续回答'),
        (23,24,'暂停'),(24,25,'取消'),(25,28,'自然收尾')]
def label(t):return next((s for a,b,s in LABELS if a<=t<b),'收尾')
def main():
    before=HERE/'board_results/previews/before_R3';after=HERE/'board_results/previews/after_R4'
    out=HERE/'previews';out.mkdir(exist_ok=True)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',21);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
    def frame(i):
        canvas=Image.new('RGB',(856,586),(250,247,242));d=ImageDraw.Draw(canvas)
        canvas.paste(Image.open(before/('%04d.png'%i)).convert('RGB'),(0,44))
        canvas.paste(Image.open(after/('%04d.png'%i)).convert('RGB'),(433,44))
        d.text((14,8),'R3 · 原有动作',font=font,fill=(70,70,70));d.text((447,8),'R4 · 对话状态驱动',font=font,fill=(110,40,60))
        d.text((16,563),'%s  |  %.2f s  |  原生离屏渲染 · 合成音量，无音频播放'%(label(i/16),i/16),font=small,fill=(70,70,70))
        return canvas
    count=len(list(after.glob('*.png')));assert count==448
    writer=cv2.VideoWriter(str(out/'dialogue_motion_16fps.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),16,(856,586));assert writer.isOpened()
    keyframes=[24,39,72,112,168,199,232,263,296,327,352,376,392,432]
    montage=Image.new('RGB',(856*2,586*7),(250,247,242))
    gif=[];reactions=[]
    for i in range(count):
        f=frame(i);writer.write(cv2.cvtColor(np.asarray(f),cv2.COLOR_RGB2BGR))
        if i in keyframes:
            n=keyframes.index(i);montage.paste(f,((n%2)*856,(n//2)*586))
        if i%2==0:gif.append(f)
        if 192<=i<344 and i%2==0:reactions.append(f)
    writer.release();montage.save(out/'contact_sheet.png');frame(199).save(out/'poster.png')
    palette_image=montage.resize((856,2051)).quantize(colors=256)
    def save_gif(name,frames):
        q=[f.quantize(palette=palette_image,dither=Image.Dither.NONE) for f in frames]
        q[0].save(out/name,save_all=True,append_images=q[1:],duration=125,loop=0,optimize=False)
    save_gif('dialogue_motion.gif',gif);save_gif('semantic_reactions.gif',reactions)
    save(out/'PREVIEW_RECEIPT.json',dict(source='Actual KV260 character GLES2 offscreen captures',frames_per_variant=448,
       model_and_textures_unchanged=True,mp4_fps=16,gif_fps=8,seconds=28,physical_screen_recording=False,
       synthesized_amplitude_only=True,audio_played=False,model_calls=0,storyboard_labels=LABELS))
    print(json.dumps({p.name:p.stat().st_size for p in out.iterdir() if p.is_file()}))
if __name__=='__main__':main()
