"""Constants shared by Pillow 8.3 on KV260 and newer PC installations."""
from PIL import Image

AFFINE = getattr(Image, 'Transform', Image).AFFINE
BICUBIC = getattr(Image, 'Resampling', Image).BICUBIC
LANCZOS = getattr(Image, 'Resampling', Image).LANCZOS
