"""Actual public-resource framing tests, skipped when optional models are absent."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))


@pytest.fixture(scope='module')
def runtimes():
    np=pytest.importorskip('numpy');s=pytest.importorskip('sherpa_onnx');pytest.importorskip('onnxruntime')
    model=Path('D:/AIModels/audio-frontend-eval-20261021/gtcrn_simple.onnx')
    if not model.exists():pytest.skip('Pinned public GTCRN resource is not provisioned')
    from board.runtime.audio.board_gtcrn_fft import FftGtcrnDenoiser
    config=s.OnlineSpeechDenoiserConfig(model=s.OfflineSpeechDenoiserModelConfig(
        gtcrn=s.OfflineSpeechDenoiserGtcrnModelConfig(model=str(model)),num_threads=1,provider='cpu'))
    return np,s.OnlineSpeechDenoiser(config),FftGtcrnDenoiser(model)


@pytest.mark.parametrize('length',[0,1,255,256,257,320,512,1001])
def test_sdk_sample_count_boundary_and_reset(runtimes,length):
    np,sdk,candidate=runtimes;sdk.reset();candidate.reset()
    samples=np.random.default_rng(19).normal(0,.02,length).astype(np.float32)
    expected=[];actual=[]
    for offset in range(0,length,73):
        expected.extend(sdk(samples[offset:offset+73],16000).samples)
        actual.extend(candidate(samples[offset:offset+73]).samples)
    expected.extend(sdk.flush().samples);actual.extend(candidate.flush().samples)
    assert len(expected)==len(actual)==length
    assert np.allclose(expected,actual,atol=1e-4,rtol=1e-4)
    assert candidate.total_input==0 and candidate.total_output==0


def test_candidate_rejects_rate_and_nonfinite_audio(runtimes):
    np,_,candidate=runtimes
    with pytest.raises(ValueError):candidate(np.zeros(320,dtype=np.float32),sample_rate=24000)
    with pytest.raises(ValueError):candidate(np.array([float('nan')],dtype=np.float32))


def test_periodic_window_is_not_symmetric_hanning(runtimes):
    np,_,candidate=runtimes
    assert candidate.window[0]==0 and candidate.window[-1]>0
    assert np.max(np.abs(candidate.window**2+np.roll(candidate.window**2,256)-1))<2e-7
