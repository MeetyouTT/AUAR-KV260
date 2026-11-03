"""Board-only premultiplied affine, with the existing Pillow coordinate system.

OpenCV is already a board dependency. Keep it to one thread in this UI process;
camera/DPU run in another process and retain their own configuration.
"""
from functools import lru_cache
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


def configure_board_rendering(core):
    cv2.setNumThreads(1)
    core.defer_portrait_offsets=True
    core._apply_offsets=fast_offsets
