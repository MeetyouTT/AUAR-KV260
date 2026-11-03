"""Resolve the selected UVC camera without relying on its videoN number."""
from pathlib import Path
import re

PINNED_CAMERA = '/dev/v4l/by-id/usb-HD_720P_Webcam_HD_720P_Webcam_20130901-video-index0'
CAMERA_IDENTITY = {'idVendor': '0c45', 'idProduct': '6341', 'serial': '20130901'}


class CameraUnavailable(RuntimeError):
    pass


def resolve_camera_device(device, video_root=Path('/sys/class/video4linux'), identity=CAMERA_IDENTITY):
    """Check the live node and USB identity before opening the capture device."""
    try:
        node = Path(device).resolve(strict=True)
        if not re.fullmatch(r'video[0-9]+', node.name) or not node.is_char_device():
            raise CameraUnavailable('Selected camera is not a V4L2 character device')
        video = video_root / node.name
        if (video/'index').read_text().strip() != '0':
            raise CameraUnavailable('Selected node is metadata, not the primary capture interface')
        usb = (video/'device').resolve(strict=True)
        usb = next((p for p in (usb, *usb.parents) if (p/'idVendor').is_file()), None)
        actual = {}
        if usb:
            actual = {key: (usb/key).read_text().strip() if (usb/key).is_file() else ''
                      for key in CAMERA_IDENTITY}
        if identity is not None and actual != identity:
            raise CameraUnavailable('Selected camera USB identity does not match the pinned camera')
        return {'configured': str(device), 'resolved': str(node), 'usb': actual,
                'usb_path': usb.name if usb else None, 'video_index': 0}
    except OSError as exc:
        raise CameraUnavailable('Waiting for selected camera: ' + str(device)) from exc
