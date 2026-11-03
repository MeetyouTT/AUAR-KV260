"""Bounded, board-peer-only real LLM probe server; never plays or opens a DB."""
import argparse
import hashlib
import json
from pathlib import Path
import signal
import sys
import threading

PROJECT = Path(__file__).resolve().parents[3]
AURA = PROJECT / 'aura'
sys.path.insert(0, str(AURA))
from tools.model_inference_host import InferenceHost, LocalModelBackend, make_server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--voice-python', required=True)
    parser.add_argument('--seconds', type=int, default=300)
    args = parser.parse_args()
    assert 30 <= args.seconds <= 600
    backend = LocalModelBackend.from_config(voice_python=args.voice_python)
    models = InferenceHost(backend)
    server = make_server(('192.168.50.1', 0), models)
    timer = threading.Timer(args.seconds, server.shutdown)
    timer.daemon = True
    timer.start()
    def stop(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    info = dict(address=server.server_address, board_peer='192.168.50.2',
                real_model=True, production_service_replaced=False,
                source_sha256=hashlib.sha256((AURA/'tools/model_inference_host.py').read_bytes()).hexdigest())
    print(json.dumps(info), flush=True)
    try:
        server.serve_forever(poll_interval=.2)
    finally:
        timer.cancel()
        server.server_close()
        models.close()


if __name__ == '__main__':
    main()
