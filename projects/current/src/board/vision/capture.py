"""One camera owner, with a newest-frame slot and source-time uncertainty."""
import hashlib
from pathlib import Path
import tempfile
import threading
import uuid
from common.contracts import FrameRef
from .frames import CapturedFrame, LatestFrameSlot


class OpenCVCamera:
    def __init__(self, config, clock):
        self.config, self.clock = config, clock
        self.epoch = uuid.uuid4().hex
        self.slot = LatestFrameSlot()
        self.error = None
        self._stop = threading.Event()
        self._thread = self._capture = self._owner = None

    def start(self):
        import cv2
        # Cooperative process lock for this framework. Legacy capture processes
        # must also be stopped before adopting its camera ownership.
        device = str(self.config["camera_device"])
        token = hashlib.sha256(device.encode()).hexdigest()[:16]
        path = Path(tempfile.gettempdir()) / ("aura-camera-" + token + ".lock")
        self._owner = path.open("a+b")
        try:
            if __import__("os").name == "nt":
                import msvcrt
                self._owner.write(b"0")
                self._owner.flush()
                self._owner.seek(0)
                msvcrt.locking(self._owner.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            source = int(device) if device.isdigit() else device
            self._capture = cv2.VideoCapture(source)
            if not self._capture.isOpened():
                raise RuntimeError("Camera could not open: " + device)
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config["width"])
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config["height"])
            self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self._thread = threading.Thread(target=self._run, name="aura-camera", daemon=True)
            self._thread.start()
            return self
        except Exception:
            self.close()
            raise

    def _run(self):
        frame_id = 0
        try:
            while not self._stop.is_set():
                captured = self.clock.now_ms()
                ok, image = self._capture.read()
                if not ok:
                    raise RuntimeError("Camera read failed")
                frame_id += 1
                height, width = image.shape[:2]
                ref = FrameRef(self.clock.domain, self.epoch, frame_id, captured, width, height,
                               "opencv_read_started_not_sensor_exposure")
                self.slot.put(CapturedFrame(ref, image))
        except Exception as exc:
            self.error = str(exc)

    def close(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._capture:
            self._capture.release()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._owner:
            self._owner.close()
            self._owner = None
