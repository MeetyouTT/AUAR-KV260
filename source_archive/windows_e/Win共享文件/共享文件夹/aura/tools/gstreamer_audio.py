"""Device audio isolated from GTK; the default PC Qt worker is unchanged."""
from pathlib import Path
from tools.realtime_audio import SelectedAudioOutput

DEFAULT_DEVICE = 'hw:CARD=MCP01,DEV=0'


class GStreamerAudioOutput(SelectedAudioOutput):
    def __init__(self, log_path=None, device=DEFAULT_DEVICE):
        super().__init__(log_path, worker_path=Path(__file__).with_name('gstreamer_audio_worker.py'),
                         worker_args=('--device', device))
