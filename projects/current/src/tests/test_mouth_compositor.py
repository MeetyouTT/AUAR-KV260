"""Regression: mouth frames must not overwrite the internal cheek/jaw edge."""
import numpy as np
import pytest
from PIL import Image
from tools.demo_script import create_demo_core
from tools.facial_layers import MouthBank
from tools.mouth_compositor import aperture_score, composite_mouth, mouth_mask


@pytest.fixture(scope='module')
def mouths():
    core = create_demo_core('reuse')
    return core, MouthBank(core)


def test_every_emotion_frame_keeps_chin_and_cheeks(mouths):
    core, _ = mouths
    protected = np.asarray(mouth_mask()) == 0
    for name, frames in core._reuse_frames.items():
        anchor = np.asarray(core._reuse_anchors[name])
        for frame in frames:
            actual = np.asarray(frame)
            assert np.array_equal(actual[158:], anchor[158:]), name
            assert np.array_equal(actual[protected], anchor[protected]), name
            assert np.array_equal(actual[:, :, 3], anchor[:, :, 3]), name


def test_interpolated_apertures_and_stop_gains_preserve_jaw(mouths):
    core, bank = mouths
    for name in bank.keys:
        anchor = np.asarray(core._reuse_anchors[name])
        assert aperture_score(bank.image(name, 1, 1)) > aperture_score(bank.image(name, 0, 1)) + 10
        for level in np.linspace(0, 1, 21):
            for gain in (0, .3, .7, 1):
                image = np.asarray(bank.image(name, level, gain))
                assert np.array_equal(image[158:], anchor[158:]), (name, level, gain)


def test_neck_color_cannot_select_an_open_mouth():
    closed = Image.new('RGBA', (464, 480), (240, 230, 220, 255))
    neck = closed.copy();neck.paste((180, 40, 50, 255), (211, 158, 241, 165))
    assert aperture_score(neck) == aperture_score(closed) == 0
    transparent = Image.new('RGBA', closed.size, (0, 0, 0, 0))
    assert np.array_equal(np.asarray(composite_mouth(closed, transparent)), np.asarray(closed))
