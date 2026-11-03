"""One background host worker; one waiting request; bounded result mailbox."""
import json
import queue
import threading
from board.runtime.dialogue_client.ws_client import WebSocketClient


class AsyncModelClient:
    def __init__(self, config, backend=None):
        self.config, self.backend = config, backend
        self.media_backend = None
        self.waiting = queue.Queue(maxsize=1)
        self.results = queue.Queue(maxsize=4)
        self.dropped_waiting = self.dropped_results = 0
        self._stop = threading.Event()
        self._client = None
        self._worker = threading.Thread(target=self._run, name="aura-model-host", daemon=True)
        self._worker.start()

    def submit(self, token, request):
        if self._stop.is_set():
            raise RuntimeError("Model client is closed")
        try:
            self.waiting.put_nowait((token, request))
        except queue.Full:
            try:
                self.waiting.get_nowait()
                self.dropped_waiting += 1
            except queue.Empty:
                pass
            self.waiting.put_nowait((token, request))

    def _call(self, request):
        if request.get("__aura_media__") is True:
            if self.media_backend is None:
                raise RuntimeError("aura-runtime-1 media transport/backend not attached")
            return self.media_backend(request["request"], pcm=request["pcm"], image_bytes=request["image_bytes"])
        if self.backend:
            return self.backend(request)
        if self.config["backend"] == "mock":
            from tools.dialogue_host_ollama import build_response
            return build_response(request, "mock", "")
        if self.config["backend"] != "websocket":
            raise RuntimeError("Model backend disabled")
        client = WebSocketClient(self.config["host"], self.config["port"], self.config["path"],
                                 timeout_s=self.config["timeout_ms"] / 1000.0)
        self._client = client
        try:
            client.connect()
            client.send_text(json.dumps(request, ensure_ascii=False, allow_nan=False))
            raw = client.recv_text()
            return json.loads(raw)
        finally:
            client.close()
            self._client = None

    def _run(self):
        while not self._stop.is_set():
            try:
                token, request = self.waiting.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                result = (token, self._call(request), None)
            except Exception as exc:
                result = (token, None, str(exc))
            try:
                self.results.put_nowait(result)
            except queue.Full:
                try:
                    self.results.get_nowait()
                    self.dropped_results += 1
                except queue.Empty:
                    pass
                self.results.put_nowait(result)

    def poll(self):
        output = []
        while True:
            try:
                output.append(self.results.get_nowait())
            except queue.Empty:
                return output

    def close(self):
        self._stop.set()
        if self._client:
            self._client.close()
        self._worker.join(timeout=1.0)
