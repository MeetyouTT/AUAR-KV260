"""Bounded, explicitly requested image questions and immutable frame metadata."""
import hashlib,re
MAX_JPEG=512*1024
def requested(text):
    if not isinstance(text,str) or len(text)>2000:return False
    t=re.sub(r'[\s，。！？?!,]','',text)
    return bool(re.search(r'(看到了?什么|看见了?什么|画面里|镜头前|摄像头前|图片里|图中|我手里|我拿的|这是什么|这东西是什么|这是什么颜色|这个是什么颜色)',t)
        or re.search(r'(看看|看一下|看一看)(我手|这个|这里|镜头|画面|这件)',t))

def validate_frame(value):
    expected={'board_boot_id','camera_epoch','frame_id','captured_mono_ms','observed_mono_ms','sha256'}
    if not isinstance(value,dict) or set(value)!=expected:raise ValueError('Invalid visual frame reference')
    if any(not isinstance(value[k],str) or not 1<=len(value[k])<=96 for k in ('board_boot_id','camera_epoch')):raise ValueError('Invalid visual epoch')
    if any(type(value[k]) is not int for k in ('frame_id','captured_mono_ms','observed_mono_ms')):raise ValueError('Invalid visual timestamp')
    if value['frame_id']<1 or not 0<=value['captured_mono_ms']<=value['observed_mono_ms']<value['captured_mono_ms']+750:raise ValueError('Stale visual frame')
    if not isinstance(value['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',value['sha256']):raise ValueError('Invalid image digest')
    return dict(value)

def validate_jpeg(frame,jpeg):
    validate_frame(frame)
    if not isinstance(jpeg,bytes) or not 100<=len(jpeg)<=MAX_JPEG or not jpeg.startswith(b'\xff\xd8') or not jpeg.endswith(b'\xff\xd9'):raise ValueError('Invalid bounded JPEG')
    if hashlib.sha256(jpeg).hexdigest()!=frame['sha256']:raise ValueError('Image differs from frame reference')

