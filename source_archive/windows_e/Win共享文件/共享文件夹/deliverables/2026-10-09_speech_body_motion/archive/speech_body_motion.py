"""Continuous head/shoulder motion for the temporary local-mouth portraits.

The same spatial transform is applied to the portrait and its eye overlay.
It is independent of mouth amplitude and keeps the hands/lower body fixed.
"""
from __future__ import annotations

import math
from typing import NamedTuple

from PIL import Image
from board.interaction.avatar_player import AvatarPlayer


class SpeechBodyPose(NamedTuple):
    dx: float = 0.0
    dy: float = 0.0
    tilt_deg: float = 0.0


NEUTRAL = SpeechBodyPose()


def smoothstep(value):
    u = max(0.0, min(1.0, value))
    return u * u * (3.0 - 2.0 * u)


class SpeechBodyMotion:
    """Fade into a global-time pose; pool rotation and quiet gaps keep phase."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.last_time = None
        self.start = 0.0
        self.duration = .7
        self.source = self.target = 0.0

    def weight(self, now):
        return self.source + (self.target - self.source) * smoothstep(
            (now - self.start) / self.duration)

    def sample(self, now, *, active, releasing=False, gain=1.0):
        if self.last_time is not None and now < self.last_time:
            self.reset()
        self.last_time = now
        if not active or gain <= 0:
            self.source = self.target = 0.0
            return NEUTRAL
        target = 0.0 if releasing else 1.0
        if target != self.target:
            self.source = self.weight(now)
            self.target = target
            self.start = now
            self.duration = .18 if releasing else .7
        weight = self.weight(now) * gain
        return SpeechBodyPose(
            weight * (2.2 * math.sin(2 * math.pi * now / 5.9)
                      + .6 * math.sin(2 * math.pi * now / 9.7)),
            weight * .9 * math.sin(2 * math.pi * now / 4.8),
            weight * .38 * math.sin(2 * math.pi * now / 7.3))


def transform_body(image, pose, *, offsets=None):
    """Warp head/hair/shoulders together, tapering to identity at y=300.

    Coordinates are defined on the existing 464x480 portraits. Normalised
    coordinates preserve the same taper if a preview is resized later.
    """
    if not pose or max(abs(value) for value in pose) < 1e-10:
        return AvatarPlayer._apply_offsets(image, offsets) if offsets else image
    width, height = image.size
    sx, sy = width / 464.0, height / 480.0
    cx, pivot_y = width / 2.0, 220.0 * sy
    affine = None
    if offsets:
        angle = math.radians(offsets.tilt_deg)
        c, s = math.cos(angle), math.sin(angle)
        scale = max(1e-6, offsets.scale_y)
        ax, ay = width / 2 + offsets.dx, height - offsets.dy
        affine = (c, -s, width / 2 - c * ax + s * ay,
                  s / scale, c / scale, height - (s * ax + c * ay) / scale)

    def source(x, y):
        weight = 1.0 - smoothstep((y / sy - 150.0) / 150.0)
        angle = math.radians(pose.tilt_deg) * weight
        c, s = math.cos(angle), math.sin(angle)
        px = x - cx - pose.dx * sx * weight
        py = y - pivot_y - pose.dy * sy * weight
        bx, by = c * px + s * py + cx, -s * px + c * py + pivot_y
        if affine:
            a, b, c, d, e, f = affine
            return a * bx + b * by + c, d * bx + e * by + f
        return bx, by

    xs = [round(width * i / 8) for i in range(9)]
    ys = sorted(set(round(y * sy) for y in
                    (0, 32, 64, 96, 128, 150, 180, 210, 240, 270,
                     300, 360, 420, 480)))
    mesh = []
    for top, bottom in zip(ys, ys[1:]):
        for left, right in zip(xs, xs[1:]):
            quad = (*source(left, top), *source(left, bottom),
                    *source(right, bottom), *source(right, top))
            mesh.append(((left, top, right, bottom), quad))
    result = image.transform(image.size, Image.Transform.MESH, mesh,
                             Image.Resampling.BILINEAR)
    # RGBA resampling can round translucent RGB even in an identity quad.
    # Restore the fixed rows exactly rather than relying on that resampler.
    fixed_y = round(300 * sy)
    if affine:
        a, b, c, d, e, f = affine
        lower = image.transform((width, height - fixed_y), Image.Transform.AFFINE,
                                (a, b, c + b * fixed_y, d, e, f + e * fixed_y),
                                Image.Resampling.BILINEAR)
    else:
        lower = image.crop((0, fixed_y, width, height))
    result.paste(lower, (0, fixed_y))
    return result
