"""Local mouth compositing for the aligned 464x480 portrait anchors.

The jaw is an internal RGB edge, not the sprite's alpha outline. Keep the
entire chin (y >= 158) and the sloping cheeks outside the feathered mouth
ellipse byte-identical to the anchor, including during interpolation.
"""
from functools import lru_cache
import numpy as np
from PIL import Image, ImageChops

MOUTH_SCORE_BOX = (214, 140, 237, 155)


@lru_cache(maxsize=1)
def mouth_mask():
    y, x = np.mgrid[:480, :464]
    radius = np.hypot((x + .5 - 225) / 14, (y + .5 - 148.5) / 9.5)
    weight = np.clip((1 - radius) / .3, 0, 1)
    weight = weight * weight * (3 - 2 * weight)
    return Image.fromarray(np.rint(weight * 255).astype('uint8'))


def composite_mouth(anchor, source):
    if anchor.size != (464, 480) or source.size != anchor.size:
        raise ValueError('Local mouths require aligned 464x480 portraits')
    # Invalid/transparent transformed source pixels must not overwrite skin.
    coverage = ImageChops.multiply(mouth_mask(), source.getchannel('A'))
    result = Image.composite(source, anchor, coverage)
    result.putalpha(anchor.getchannel('A'))
    return result


def aperture_score(image):
    # The former y=165 window counted pink neck/jaw pixels as an open mouth.
    crop = np.asarray(image.crop(MOUTH_SCORE_BOX), dtype=float)
    r, g, b = crop[:, :, 0], crop[:, :, 1], crop[:, :, 2]
    return int(np.sum((r > g * 1.35) & (r > b * 1.1) & (r > 50) & (g < 170)))
