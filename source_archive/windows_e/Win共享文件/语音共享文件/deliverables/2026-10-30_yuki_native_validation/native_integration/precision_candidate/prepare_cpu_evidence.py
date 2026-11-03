"""Generate small C++ source-rectangle fixture and independent sampling evidence.

Reads original source JSON/PNG, writes only precision_candidate files. This is
not a native/GPU test. IEEE-half estimates are not actual Mali measurements.
"""
from pathlib import Path
import hashlib
import json
import math
import struct
try:
    from PIL import Image
except ImportError:
    Image=None

HERE=Path(__file__).resolve().parent
BASE=HERE.parent.parent
SOURCE=BASE/'inputs/ems/yuk_0.ems.json'
PNG=BASE/'inputs/ems/yuk_0.ems/tex-texture.png'
doc=json.loads(SOURCE.read_text(encoding='utf8'))
rows=[]
for name,rect in sorted(doc['source']['tex']['icon'].items()):
    x=max(0,math.floor(rect['left'])-2);y=max(0,math.floor(rect['top'])-2)
    endx=min(4096,math.ceil(rect['left']+rect['width'])+2)
    endy=min(4096,math.ceil(rect['top']+rect['height'])+2)
    rows.append(dict(name=name,left=rect['left'],top=rect['top'],width=rect['width'],height=rect['height'],
                     attr=rect['attr'],crop=[x,y,endx-x,endy-y]))
def cpp_float(value):
    text=format(float(value),'.9g')
    if '.' not in text and 'e' not in text:text+='.0'
    return text+'f'
header=['// SPDX-License-Identifier: AGPL-3.0-only',
        '// Source rectangles only; generated from the pinned EMS JSON. No pixels.',
        '#pragma once','#include <nekomote/model/asset.hpp>','#include <array>',
        'struct YukiIconFixture { const char* name; float left,top,width,height; int attr; };',
        'inline constexpr std::array<YukiIconFixture,68> yuki_icons{{']
for r in rows:
    header.append(' {"'+r['name']+'",'+','.join(cpp_float(r[k]) for k in ['left','top','width','height'])+','+str(r['attr'])+'},')
header+=['}};','inline void load_yuki_icons(nekomote::model::ModelAsset& asset) {',
         ' for(const auto& r:yuki_icons)asset.icons.emplace(std::string("tex/")+r.name,',
         '  nekomote::model::IconRect{"tex",r.left,r.top,r.width,r.height,0,0,r.attr,0});','}']
(HERE/'yuki_icons_fixture.hpp').write_text('\n'.join(header)+'\n',encoding='utf8')

f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
half=lambda x:struct.unpack('<e',struct.pack('<e',x))[0]
class PatternImage:
    def __init__(self,w=4096,h=4096,x=0,y=0):self.width=w;self.height=h;self.x=x;self.y=y
    def getpixel(self,xy):
        x,y=xy;x+=self.x;y+=self.y
        return ((17*x+11*y)%256,(7*x+29*y)%256,((x//3)^(y//5))*43%256,(13*x+23*y)%256)
    def crop(self,box):
        x,y,r,b=box
        return PatternImage(r-x,b-y,self.x+x,self.y+y)
atlas=Image.open(PNG).convert('RGBA') if Image else PatternImage()
def bilinear(image,u,v):
    x=u*image.width-.5;y=v*image.height-.5
    ix=math.floor(x);iy=math.floor(y);fx=x-ix;fy=y-iy
    at=lambda xx,yy:image.getpixel((max(0,min(image.width-1,xx)),max(0,min(image.height-1,yy))))
    p00,p10,p01,p11=at(ix,iy),at(ix+1,iy),at(ix,iy+1),at(ix+1,iy+1)
    return [(1-fy)*((1-fx)*a+fx*b)+fy*((1-fx)*c+fx*d) for a,b,c,d in zip(p00,p10,p01,p11)]

ideal_error=0.;float_error=0.;reconstruction_error=0.;samples=0;pixel_samples=0
atlas_half_errors=[];tile_half_errors=[]
fractions=[0,.137,.333,.5,.677,.9,1]
for r in rows:
    x,y,w,h=r['crop'];tile=atlas.crop((x,y,x+w,y+h))
    errors_atlas=[];errors_tile=[]
    for fx in fractions:
        for fy in fractions:
            # Preserve the source's Float32 normalized UVs, then apply the exact
            # affine mapping used by the C++ adapter in double->float32.
            u=f32((r['left']+fx*r['width'])/4096);v=f32((r['top']+fy*r['height'])/4096)
            lu=(u*4096-x)/w;lv=(v*4096-y)/h
            flu,flv=f32(lu),f32(lv)
            reconstruction_error=max(reconstruction_error,abs(flu*w+x-u*4096),abs(flv*h+y-v*4096))
            ideal=bilinear(atlas,u,v);local=bilinear(tile,lu,lv);floating=bilinear(tile,flu,flv)
            ideal_error=max(ideal_error,max(abs(a-b) for a,b in zip(ideal,local)))
            float_error=max(float_error,max(abs(a-b) for a,b in zip(ideal,floating)))
            ea=max(abs(half(u)*4096-u*4096),abs(half(v)*4096-v*4096))
            et=max(abs(half(flu)*w+x-u*4096),abs(half(flv)*h+y-v*4096))
            errors_atlas.append(ea);errors_tile.append(et);samples+=1;pixel_samples+=1
    r['ieee_half_estimate']={'atlas_mean_xy_max_error_pixels':sum(errors_atlas)/len(errors_atlas),
        'local_mean_xy_max_error_pixels':sum(errors_tile)/len(errors_tile),
        'atlas_max_error_pixels':max(errors_atlas),'local_max_error_pixels':max(errors_tile)}
    atlas_half_errors.extend(errors_atlas);tile_half_errors.extend(errors_tile)
    # Include bilinear taps a half texel outside each icon. Original atlas
    # neighbours, not a duplicated icon-edge strip, must be present in the tile.
    for px,py in [(r['left']-.4,r['top']-.4),(r['left']+r['width']+.4,r['top']+r['height']+.4)]:
        u=px/4096;v=py/4096
        a=bilinear(atlas,u,v);b=bilinear(tile,(px-x)/w,(py-y)/h)
        ideal_error=max(ideal_error,max(abs(c-d) for c,d in zip(a,b)));pixel_samples+=1
pixels=sum(r['crop'][2]*r['crop'][3] for r in rows)
power2=lambda n:1<<(n-1).bit_length()
evidence={'scope':'Python independent layout/sampling evidence only; C++ and actual GLES pending parent validation',
    'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'atlas_png':str(PNG),'atlas_png_sha256':hashlib.sha256(PNG.read_bytes()).hexdigest(),
    'tile_count':len(rows),'border_pixels':2,'sum_pixels':pixels,'tile_rgba_bytes':pixels*4,
    'power2_rounded_upper_rgba_bytes':sum(power2(r['crop'][2])*power2(r['crop'][3])*4 for r in rows),
    'original_atlas_rgba_bytes':4096*4096*4,
    'maximum_width':max(r['crop'][2] for r in rows),'maximum_height':max(r['crop'][3] for r in rows),
    'sampling':{'image':'actual atlas RGBA' if Image else 'procedural RGBA+alpha pattern on the real atlas layout; PIL unavailable, no original pixel decode claimed',
                'samples':pixel_samples,'max_ideal_bilinear_rgba_error_0_to_255':ideal_error,
                'max_float32_local_rgba_error_0_to_255':float_error,
                'max_float32_atlas_pixel_coordinate_roundtrip_error':reconstruction_error},
    'ieee_half_estimate':{'not_gpu_measurement':True,'samples':samples,
        'atlas_mean_xy_max_error_pixels':sum(atlas_half_errors)/len(atlas_half_errors),
        'local_mean_xy_max_error_pixels':sum(tile_half_errors)/len(tile_half_errors),
        'atlas_max_error_pixels':max(atlas_half_errors),'local_max_error_pixels':max(tile_half_errors)},
    'icons':rows,'cpp_compiled':False,'gpu_tested':False,'production_modified':False}
assert len(rows)==68 and pixels*4==27415660
assert ideal_error<1e-8 and reconstruction_error<.0005
(HERE/'cpu-layout-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in evidence.items() if k not in ['icons','source','atlas_png']},indent=2))
