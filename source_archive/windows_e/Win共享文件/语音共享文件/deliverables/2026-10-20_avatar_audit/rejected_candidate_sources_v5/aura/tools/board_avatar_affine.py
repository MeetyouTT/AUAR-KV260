"""Board-only premultiplied affine, with the existing Pillow coordinate system.

OpenCV is already a board dependency. Keep it to one thread in this UI process;
camera/DPU run in another process and retain their own configuration.
"""
from functools import lru_cache
from functools import partial
import math
import cv2
import numpy as np
from PIL import Image


@lru_cache(maxsize=4)
def _centres(size):
    w,h=size
    return np.arange(w,dtype=np.float32)[None,:]+.5,np.arange(h,dtype=np.float32)[:,None]+.5


def affine_rgba(image,inverse):
    """Bilinear interpolation in premultiplied alpha; no dark edge halo."""
    if image.mode!='RGBA':raise ValueError('Expected RGBA avatar')
    a,b,c,d,e,f=inverse
    # Pillow evaluates pixel centres; OpenCV places centres on integer indices.
    matrix=np.array([[a,b,c+(a+b-1)*.5],[d,e,f+(d+e-1)*.5]],dtype=np.float64)
    raw=np.frombuffer(image.convert('RGBa').tobytes(),dtype=np.uint8).reshape(image.height,image.width,4)
    transformed=cv2.warpAffine(raw,matrix,image.size,flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP,
                               borderMode=cv2.BORDER_REPLICATE)
    # Pillow clamps interpolation at an edge only for centres inside the source.
    x,y=_centres(image.size);sx=a*x+b*y+c;sy=d*x+e*y+f
    outside=(sx<0)|(sx>=image.width)|(sy<0)|(sy>=image.height)
    transformed[outside]=0
    return Image.frombytes('RGBa',image.size,transformed.tobytes()).convert('RGBA')


def fast_offsets(image,off):
    w,h=image.size;angle=math.radians(off.tilt_deg);c,s=math.cos(angle),math.sin(angle)
    sy=max(1e-6,off.scale_y);cx,cy=w/2.0+off.dx,h-off.dy
    return affine_rgba(image,(c,-s,w/2.0-c*cx+s*cy,s/sy,c/sy,h-(s*cx+c*cy)/sy))


def _clear_edges(result,coefficients,source_size,background):
    """Exact Pillow boundary rule, evaluated only in the possible edge strips."""
    h,w=result.shape[:2];sw,sh=source_size;a,b,c,d,e,f=coefficients
    sx,sy=sw/w,sh/h
    displacement=max(abs((a-sx)*x+b*y+c) for x,y in ((0,0),(w,0),(0,h),(w,h)))
    displacement=max(displacement,max(abs(d*x+(e-sy)*y+f) for x,y in ((0,0),(w,0),(0,h),(w,h))))
    margin=int(math.ceil(displacement/min(sx,sy)))+2
    regions=((0,0,w,h),) if 2*margin>=min(w,h) else ((0,0,w,margin),(0,h-margin,w,h),(0,margin,margin,h-margin),(w-margin,margin,w,h-margin))
    xs,ys=_centres((w,h))
    for left,top,right,bottom in regions:
        x,y=xs[:,left:right],ys[top:bottom,:]
        xx=a*x+b*y+c;yy=d*x+e*y+f
        result[top:bottom,left:right][(xx<0)|(xx>=sw)|(yy<0)|(yy>=sh)]=background


def fast_offsets_rgb(image,off,*,background,output_size=None):
    """Composite before affine: interpolation commutes with a constant backdrop.

    This avoids RGBA -> RGBa -> RGBA -> RGB on every board frame. All local
    mouth/eye composition is already finished before this final display step.
    """
    w,h=image.size;angle=math.radians(off.tilt_deg);c,s=math.cos(angle),math.sin(angle)
    sy=max(1e-6,off.scale_y);cx,cy=w/2.0+off.dx,h-off.dy
    a,b,tx,d,e,ty=(c,-s,w/2.0-c*cx+s*cy,s/sy,c/sy,h-(s*cx+c*cy)/sy)
    flat=Image.new('RGB',image.size,background);flat.paste(image,mask=image.getchannel('A'))
    raw=np.frombuffer(flat.tobytes(),dtype=np.uint8).reshape(h,w,3)
    size=tuple(output_size or image.size);sx,sy=w/size[0],h/size[1]
    a,b,d,e=a*sx,b*sy,d*sx,e*sy
    m=np.array([[a,b,tx+(a+b-1)*.5],[d,e,ty+(d+e-1)*.5]],dtype=np.float64)
    result=cv2.warpAffine(raw,m,size,flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_REPLICATE)
    _clear_edges(result,(a,b,tx,d,e,ty),image.size,background)
    return Image.frombytes('RGB',size,result.tobytes())


def configure_board_rendering(core,background='white',output_size=None):
    cv2.setNumThreads(1)
    core.defer_portrait_offsets=True
    color=Image.new('RGB',(1,1),background).getpixel((0,0))
    core._apply_offsets=partial(fast_offsets_rgb,background=color,output_size=output_size)
    core.blend_frames=fast_blend


def fast_blend(a,b,alpha):
    if alpha<=0:return a
    if alpha>=1:return b
    if a.size!=b.size or a.mode!=b.mode:raise ValueError('Mismatched avatar frames')
    channels=len(a.getbands());shape=(a.height,a.width,channels)
    x=np.frombuffer(a.tobytes(),dtype=np.uint8).reshape(shape)
    y=np.frombuffer(b.tobytes(),dtype=np.uint8).reshape(shape)
    return Image.frombytes(a.mode,a.size,cv2.addWeighted(x,1-alpha,y,alpha,0).tobytes())


def resize_rgb(image,size):
    if image.mode!='RGB':raise ValueError('Expected flattened RGB avatar')
    if image.size==tuple(size):return image.tobytes()
    raw=np.frombuffer(image.tobytes(),dtype=np.uint8).reshape(image.height,image.width,3)
    return cv2.resize(raw,tuple(size),interpolation=cv2.INTER_CUBIC).tobytes()
