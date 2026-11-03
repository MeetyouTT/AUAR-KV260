"""Offscreen real-material preview. No device, camera, synthesis or new bitmap art."""
import visual_bootstrap
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
from tools.demo_script import create_demo_core
from tools.realtime_facials import RealtimeFacials
from tools.idle_body_compositor import seed_speaking_materials,material_variant
H=Path(__file__).resolve().parent
core=create_demo_core('reuse');core.idle_gain=0
facials=RealtimeFacials(core,expressive_body=True);facials.body.warmup()
cases=[('neutral-a','SPEAKING_NEUTRAL',0),('neutral-b','SPEAKING_NEUTRAL',2),
 ('happy','SPEAKING',4),('sad','SPEAKING_LOW',6)]
tiles=[];metadata=[]
for label,state,generation in cases:
 core.reset_playback();facials.body.player.reset_playback();core.talk_gen=generation
 core.reply_text='公开素材对齐预览';core.emotion='sad' if state=='SPEAKING_LOW' else 'happy' if state=='SPEAKING' else 'neutral'
 seed_speaking_materials(core,generation,0)
 for index,(gain,level,now) in enumerate([(0.,0.,.4),(1.,.75,.5),(1.,.75,1.4)]):
  meta=core.display_frame(state,now);result=facials.apply(meta,now,gain,level)
  image=result['image'];assert image.mode=='RGBA' and image.size==(464,480)
  assert np.array_equal(np.asarray(image.getchannel('A')),np.asarray(facials.body.player.frame_at(facials.body.BODY_STATES[result['body_asset']],now)['image'].getchannel('A')))
  metadata.append({'label':label,'state':state,'generation':generation,'mouth_asset':result['asset'],
   'body_asset':result['body_asset'],'body_index':result['body_index'],'gain':gain,'level':level,
   'blink_active':result['blink_active'],'variant':material_variant(generation,2)})
  flat=Image.new('RGB',image.size,'#FCFCF3');flat.paste(image,mask=image.getchannel('A'))
  tile=Image.new('RGB',(232,265),'#FCFCF3');tile.paste(flat.resize((232,240)),(0,25));ImageDraw.Draw(tile).text((4,5),label+': '+('closed' if not gain else 'blink' if result['blink_active'] else 'speech'),fill='black')
  tiles.append(tile)
page=Image.new('RGB',(232*3,265*4),'#FCFCF3')
for i,tile in enumerate(tiles):page.paste(tile,((i%3)*232,(i//3)*265))
page.save(H/'visual_preview.png')
(H/'visual_preview.json').write_text(json.dumps({'status':'PASS','cases':metadata,'device_opened':False,'microphone_opened':False},indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','preview':str(H/'visual_preview.png'),'body_assets':sorted({row['body_asset'] for row in metadata})}))
