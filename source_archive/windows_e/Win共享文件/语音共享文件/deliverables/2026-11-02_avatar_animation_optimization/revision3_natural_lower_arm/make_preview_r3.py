from common import *
from PIL import Image,ImageDraw,ImageFont
import cv2,numpy as np
def main():
 before=HERE/'board_results/previews/before_R2';after=HERE/'board_results/previews/after_R3'
 out=HERE/'previews';out.mkdir(exist_ok=True)
 font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
 small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
 def pair(i):
  a=Image.open(before/('%04d.png'%i)).convert('RGB');b=Image.open(after/('%04d.png'%i)).convert('RGB')
  image=Image.new('RGB',(856,570),(250,247,242));image.paste(a,(0,40));image.paste(b,(433,40));d=ImageDraw.Draw(image)
  d.text((16,8),'R2',font=font,fill=(70,70,70));d.text((449,8),'R3 · 下层臂收小放缓',font=font,fill=(100,40,50))
  d.text((16,550),'同模型 / 同尺寸 / 同种子 / 同时间轴    %.2f s'%(i/16),font=small,fill=(70,70,70))
  return image
 frames=[pair(i) for i in range(192)]
 writer=cv2.VideoWriter(str(out/'before_after_16fps.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),16,(856,570))
 assert writer.isOpened()
 for f in frames:writer.write(cv2.cvtColor(np.asarray(f),cv2.COLOR_RGB2BGR))
 writer.release()
 montage=Image.new('RGB',(856*3,570*2),(250,247,242))
 for n,i in enumerate((32,64,88,112,144,176)):montage.paste(frames[i],((n%3)*856,(n//3)*570))
 montage.save(out/'contact_sheet.png');frames[88].save(out/'poster.png')
 # GIF is an 8 fps convenience preview. The MP4 retains the original 16 fps.
 gif=frames[::2];palette=montage.quantize(colors=256).getpalette()
 p=Image.new('P',(1,1));p.putpalette(palette)
 quantized=[f.quantize(palette=p,dither=Image.Dither.NONE) for f in gif]
 quantized[0].save(out/'before_after.gif',save_all=True,append_images=quantized[1:],duration=125,loop=0,optimize=False)
 save(out/'PREVIEW_RECEIPT.json',dict(source='Actual KV260 offscreen GLES2 character captures',frames_per_variant=192,width=423,height=516,synthetic_timeline_seconds=12,mp4_fps=16,gif_fps=8,physical_screen_recording=False,playback_audio=False,engineering_export_modified=False))
 print(json.dumps({p.name:p.stat().st_size for p in out.iterdir() if p.is_file()}))
if __name__=='__main__':main()
