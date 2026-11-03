"""Exercise USB identity, node renumbering and capture/metadata separation."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from board.vision.camera_device import CAMERA_IDENTITY, CameraUnavailable, resolve_camera_device
from board.vision.ui_camera_service import video_owners


class CameraDeviceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.video = self.root/'video-class'
        self.video.mkdir()
        self.usb = self.root/'usb-port-3'
        self.usb.mkdir()
        for name, value in CAMERA_IDENTITY.items():
            (self.usb/name).write_text(value)
        self.interface = self.usb/'interface'
        self.interface.mkdir()
        self.link = self.root/'fixed-camera'

    def node(self, number, index='0'):
        node = self.root/('video'+str(number))
        node.touch()
        folder = self.video/node.name
        folder.mkdir()
        (folder/'index').write_text(index)
        (folder/'device').symlink_to(self.interface, target_is_directory=True)
        return node

    def resolve(self):
        with patch.object(Path, 'is_char_device', return_value=True):
            return resolve_camera_device(self.link, self.video)

    def test_same_camera_survives_video_number_change(self):
        first = self.node(0)
        self.link.symlink_to(first)
        self.assertEqual(self.resolve()['resolved'], str(first))
        first.unlink()
        self.link.unlink()
        second = self.node(4)
        self.link.symlink_to(second)
        result = self.resolve()
        self.assertEqual(result['resolved'], str(second))
        self.assertEqual(result['usb'], CAMERA_IDENTITY)

    def test_absent_or_dangling_link_waits_for_selected_camera(self):
        with self.assertRaises(CameraUnavailable):
            self.resolve()
        self.link.symlink_to(self.root/'video9')
        with self.assertRaises(CameraUnavailable):
            self.resolve()

    def test_metadata_node_is_not_opened_as_video(self):
        self.link.symlink_to(self.node(1, '1'))
        with self.assertRaisesRegex(CameraUnavailable, 'metadata'):
            self.resolve()

    def test_wrong_usb_identity_is_rejected(self):
        self.link.symlink_to(self.node(0))
        for field in CAMERA_IDENTITY:
            with self.subTest(field=field):
                (self.usb/field).write_text('different')
                with self.assertRaisesRegex(CameraUnavailable, 'identity'):
                    self.resolve()
                (self.usb/field).write_text(CAMERA_IDENTITY[field])

    def test_regular_file_is_not_a_camera(self):
        self.link.symlink_to(self.node(0))
        with self.assertRaisesRegex(CameraUnavailable, 'character device'):
            resolve_camera_device(self.link, self.video)

    def test_no_silent_fallback_to_another_video_node(self):
        self.node(0)
        with self.assertRaises(CameraUnavailable):
            self.resolve()

    def test_device_alias_does_not_bypass_existing_owner(self):
        node = self.node(0)
        self.link.symlink_to(node)
        proc = self.root/'proc'
        fd = proc/'987654'/'fd'
        fd.mkdir(parents=True)
        (fd/'3').symlink_to(node)
        self.assertEqual(video_owners(str(self.link), proc), [987654])


if __name__ == '__main__':
    unittest.main()
