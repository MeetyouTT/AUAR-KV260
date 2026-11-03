"""Conservative first-turn ASR gate, not speaker or semantic intent recognition."""
import re
import array
import sys


def audio_candidate(pcm):
    """Same 16kHz/20ms/180ms RMS floor as the board endpoint, before ASR.

    An ASR can hallucinate words for all-zero audio. Transcription alone must
    never bypass the board's original evidence of sustained acoustic activity.
    This energy check does not classify a speaker or exclude television audio.
    """
    if not isinstance(pcm,bytes) or len(pcm)%2:return False
    samples=array.array('h');samples.frombytes(pcm)
    if sys.byteorder!='little':samples.byteswap()
    consecutive=0
    for pos in range(0,len(samples)-319,320):
        frame=samples[pos:pos+320]
        above=sum(int(value)*int(value) for value in frame)/320 >= (.010*32768)**2
        consecutive=consecutive+1 if above else 0
        if consecutive>=9:return True
    return False


def acceptable_entry(text):
    if not isinstance(text,str):return False
    compact=re.sub(r'[^\w\u4e00-\u9fff]','',text.lower())
    if len(compact)<2:return False
    if compact in {'嗯嗯','啊啊','呃呃','哈哈','谢谢观看','感谢观看','字幕','音乐','静音','无声'}:return False
    return bool(re.search(r'[a-z\u4e00-\u9fff]',compact))


class EntryRejected(ValueError):
    pass
