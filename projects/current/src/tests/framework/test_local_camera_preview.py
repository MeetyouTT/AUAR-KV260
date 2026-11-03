"""RAM frame transport must reject torn, stale, foreign and replayed frames."""
import os
from pathlib import Path
import tempfile
import unittest

from board.vision.local_preview import PIXELS, RawFrameReader, RawFrameStore, unpack
from board.interaction.ui_services import UiServiceClient


class LocalPreviewTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.owner={'board_boot_id':'boot','service_epoch':'service','camera_epoch':'a'*32}
        self.store=RawFrameStore(self.owner,self.directory.name)
        self.addCleanup(self.store.close)
        self.reader=RawFrameReader(self.owner,self.directory.name)
        self.pixels=bytes([20,60,120])*(640*480)

    def test_latest_frame_is_complete_private_and_not_repeated(self):
        self.store.publish(1,1000,self.pixels)
        header,pixels=self.reader.read(1010)
        self.assertEqual(header['frame_id'],1)
        self.assertEqual(pixels,self.pixels)
        self.assertEqual(self.store.path.stat().st_mode&0o777,0o600)
        self.assertIsNone(self.reader.read(1020))
        self.store.publish(3,1030,bytes(PIXELS))
        self.assertEqual(self.reader.read(1040)[0]['frame_id'],3)
        self.assertEqual(len(list(Path(self.directory.name).iterdir())),1)

    def test_stale_future_truncated_or_extra_bytes_rejected(self):
        self.store.publish(1,1000,self.pixels)
        data=self.store.path.read_bytes()
        for blob,now in ((data,1250),(data,899),(data[:-1],1000),(data+b'x',1000),(b'bad',1000)):
            with self.subTest(now=now,size=len(blob)),self.assertRaises(ValueError):unpack(blob,self.owner,now)

    def test_cross_boot_service_and_camera_owners_rejected(self):
        self.store.publish(1,1000,self.pixels)
        for key in self.owner:
            owner=dict(self.owner,**{key:'foreign'})
            with self.subTest(key=key),self.assertRaises(ValueError):unpack(self.store.path.read_bytes(),owner,1000)

    def test_rollback_rejected_and_existing_file_preserved(self):
        self.store.publish(4,1000,self.pixels);self.reader.read(1001)
        with self.assertRaises(FileExistsError):RawFrameStore(self.owner,self.directory.name)
        self.store.publish(3,1010,self.pixels)
        with self.assertRaises(ValueError):self.reader.read(1011)

    def test_symlink_and_world_readable_transport_rejected(self):
        self.store.publish(1,1000,self.pixels)
        os.chmod(str(self.store.path),0o644)
        with self.assertRaises(ValueError):self.reader.read(1001)
        os.chmod(str(self.store.path),0o600)
        other=self.store.path.with_name('other');other.symlink_to(self.store.path)
        self.reader.path=other
        with self.assertRaises(OSError):self.reader.read(1001)

    def test_local_transport_requires_opt_in_actual_source_and_loopback(self):
        client=UiServiceClient.__new__(UiServiceClient);client.local_raw=True
        snapshot={'source_kind':'actual','modules':{'camera':{'preview_transport':'aura-local-bgr-1'}}}
        self.assertTrue(client.use_raw(snapshot,{'host':'127.0.0.1'}))
        self.assertFalse(client.use_raw(snapshot,{'host':'192.168.1.2'}))
        snapshot['source_kind']='fixture'
        self.assertFalse(client.use_raw(snapshot,{'host':'127.0.0.1'}))
        snapshot['source_kind']='actual';client.local_raw=False
        self.assertFalse(client.use_raw(snapshot,{'host':'127.0.0.1'}))


if __name__=='__main__':unittest.main()
