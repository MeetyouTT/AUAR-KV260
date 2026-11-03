"""Three measured pointing anchors for an independent, stationary camera.

This maps image positions to pulse targets; it cannot infer physical shaft
angle or verify pointing accuracy. No calibration values are supplied by default.
"""
from dataclasses import dataclass
import math

REFERENCE_X_PX = 320
IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480


@dataclass(frozen=True)
class FixedViewMapping:
    boot_id: str
    setup_id: str
    camera_epoch: str
    reference_us: int
    polarity: int
    left_x_px: float
    left_us: int
    right_x_px: float
    right_us: int
    evidence: str
    confirmed: bool

    def __post_init__(self):
        if (not self.boot_id or not self.setup_id or not self.camera_epoch or not self.evidence
                or self.confirmed is not True or type(self.polarity) is not int or self.polarity not in (-1,1)
                or any(type(v) is not int or not 1400 <= v <= 1600
                       for v in (self.reference_us,self.left_us,self.right_us))
                or any(type(v) not in (int,float) or not math.isfinite(v)
                       for v in (self.left_x_px,self.right_x_px))
                or not 0 <= self.left_x_px < REFERENCE_X_PX < self.right_x_px < IMAGE_WIDTH
                or self.polarity*(self.left_us-self.reference_us) >= 0
                or self.polarity*(self.right_us-self.reference_us) <= 0):
            raise ValueError('Measured left/blue-line/right anchors and matching setup are required')

    def matches(self, reference, camera_epoch):
        return (reference.camera_moves_with_axis is False
                and (self.boot_id,self.setup_id,self.reference_us,self.polarity,self.camera_epoch)
                == (reference.boot_id,reference.setup_id,reference.reference_us,reference.polarity,camera_epoch))

    def target_us(self, center_x):
        if type(center_x) not in (int,float) or not math.isfinite(center_x):
            raise ValueError('Finite image position required')
        x = max(self.left_x_px,min(self.right_x_px,center_x))
        if x < REFERENCE_X_PX:
            return self.reference_us + (self.left_us-self.reference_us)*(REFERENCE_X_PX-x)/(REFERENCE_X_PX-self.left_x_px)
        return self.reference_us + (self.right_us-self.reference_us)*(x-REFERENCE_X_PX)/(self.right_x_px-REFERENCE_X_PX)
