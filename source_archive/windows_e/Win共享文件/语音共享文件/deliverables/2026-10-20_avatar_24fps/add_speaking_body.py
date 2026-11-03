"""Reuse the existing tracked idle-body compositor in the native live path."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;APP=HERE.parents[1]/'aura'
source=HERE/'action_support_remote/aura/tools'
out=HERE/'action_sources/tools'
text=(source/'realtime_facials.py').read_text(encoding='utf-8')
text=text.replace('from board.interaction.avatar_timing import idle_offsets',
    'from board.interaction.avatar_timing import idle_offsets\nfrom tools.idle_body_compositor import IdleBodyTrack,composite_idle_mouth')
text=text.replace('        core.audio_mouth_assets=frozenset(self.mouths.keys)',
    '        core.audio_mouth_assets=frozenset(self.mouths.keys)\n        self.body=IdleBodyTrack(core)')
text=text.replace("        result=dict(meta);asset=meta['asset'];result.update(speech_gain=gain,mouth_level=level)",
"""        result=dict(meta);asset=meta['asset'];result.update(speech_gain=gain,mouth_level=level)
        body,face=self.body.sample(now)
        if asset in self.mouths.keys or meta.get('display_state')=='IDLE':
            result.update(body_asset=body['asset'],body_index=body['index'],
                          body_source_position=body['source_position'],body_face_matrix=face.tolist())
            result['image']=body['image']""")
text=text.replace('            image=self.mouths.image(asset,level,gain)',
"""            mouth=self.mouths.image(asset,level,1)
            image=composite_idle_mouth(body['image'],mouth,self.body.mouth_matrix(asset,face),gain)""")
(out/'realtime_facials.py').write_text(text,encoding='utf-8')
text=(APP/'tools/idle_body_compositor.py').read_text(encoding='utf-8')
text=text.replace('from PIL import Image, ImageChops',
    "from PIL import Image, ImageChops\nfrom tools.pillow_compat import AFFINE\nBILINEAR=getattr(Image,'Resampling',Image).BILINEAR")
text=text.replace('Image.Transform.AFFINE','AFFINE').replace('Image.Resampling.BILINEAR','BILINEAR')
# Avoid a threaded LAPACK call for a six-coefficient affine inverse.
text=text.replace("    inverse = np.linalg.inv(np.vstack((m, [0, 0, 1])))[:2]\n    a, b, c = inverse[0]; d, e, f = inverse[1]",
"""    ma,mb,mc=m[0];md,me,mf=m[1];det=ma*me-mb*md
    if abs(det)<1e-8:raise ValueError('Singular tracked mouth transform')
    a,b,c,d,e,f=me/det,-mb/det,(mb*mf-me*mc)/det,-md/det,ma/det,(md*mc-ma*mf)/det""")
(out/'idle_body_compositor.py').write_text(text,encoding='utf-8')
text=(source/'facial_layers.py').read_text(encoding='utf-8')
text=text.replace('    def overlay(self,asset,t,index=0):','    def overlay(self,asset,t,index=0,pose=None):')
text=text.replace('        if asset not in self.ALIASES:',
                  '        if pose is not None:layer=warp(layer,pose)\n        elif asset not in self.ALIASES:')
text=text.replace("        layer,phase=self.overlay(meta['asset'],t,meta.get('index',0))",
"""        if 'body_face_matrix' in meta:
            layer,phase=self.overlay('idle_normal',t,meta.get('body_index',0),pose=meta['body_face_matrix'])
        else:layer,phase=self.overlay(meta['asset'],t,meta.get('index',0))""")
(out/'facial_layers.py').write_text(text,encoding='utf-8')
print('Existing tracked body and facial layers connected')
