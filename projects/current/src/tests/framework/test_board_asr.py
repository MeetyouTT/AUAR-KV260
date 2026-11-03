import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from board.runtime.audio.board_asr import BoardAsrUnavailable, BoardParaformer


def create(tmp_path, **kwargs):
    for name in ('model.int8.onnx','tokens.txt'):(tmp_path/name).write_bytes(b'synthetic resource')
    digest=hashlib.sha256(b'synthetic resource').hexdigest()
    class Decoder:
        def create_stream(self):
            return SimpleNamespace(accept_waveform=lambda rate,samples:None,
                                   result=SimpleNamespace(text='公开测试'))
        def decode_stream(self,stream):
            if kwargs.get('after_decode'):kwargs['after_decode']()
    def factory(**options):
        assert options['paraformer'].endswith('model.int8.onnx')
        assert options['num_threads']==2 and options['sample_rate']==16000
        return Decoder()
    return BoardParaformer(tmp_path,model_sha256=digest,tokens_sha256=digest,
        clock=kwargs.get('clock',lambda:0.),recognizer_factory=factory)


def test_asr_strict_resources_and_original_deadline(tmp_path):
    decoder=create(tmp_path)
    assert decoder.transcribe(b'\0\0'*160,deadline=10)=='公开测试'
    (tmp_path/'model.int8.onnx').write_bytes(b'changed')
    with pytest.raises(BoardAsrUnavailable):
        BoardParaformer(tmp_path,model_sha256='0'*64,tokens_sha256='0'*64)


@pytest.mark.parametrize('pcm,rate',[(b'',16000),(b'x',16000),(b'\0\0',24000),(b'\0\0'*320001,16000)],
                         ids=['empty','odd','wrong_rate','too_long'])
def test_invalid_audio_cannot_reach_decoder(tmp_path,pcm,rate):
    with pytest.raises(ValueError):create(tmp_path).transcribe(pcm,sample_rate=rate,deadline=10)


def test_cancelled_or_expired_result_is_discarded(tmp_path):
    now=[0.]
    decoder=create(tmp_path,clock=lambda:now[0],after_decode=lambda:now.__setitem__(0,2.))
    with pytest.raises(TimeoutError):decoder.transcribe(b'\0\0',deadline=1)
    with pytest.raises(InterruptedError):decoder.transcribe(b'\0\0',deadline=10,cancelled=lambda:True)
