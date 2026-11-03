#!/usr/bin/env python3
"""Compare the compatibility backend with real OpenCV 4.6.0 APIs."""
import hashlib,json,time
from pathlib import Path
import cv2,numpy as np
from face_compat import YuNetCompat,SFaceCompat
ROOT=Path(__file__).resolve().parent
image=cv2.imread(str(ROOT/'reference/lena.jpg'))
compat=YuNetCompat(ROOT/'models/yunet_2022mar.onnx')
native=cv2.FaceDetectorYN.create(str(ROOT/'models/yunet_2022mar.onnx'),'',(320,320),.9,.3,5000)
recognizer=SFaceCompat(ROOT/'models/sface_2021dec.onnx')
native_sf=cv2.FaceRecognizerSF.create(str(ROOT/'models/sface_2021dec.onnx'),'')
cv2.setNumThreads(2)
result={'opencv':cv2.__version__,'tests':[],'role':'CPU_REFERENCE'}
samples=[('original',image),('resized',cv2.resize(image,(640,480))),('flipped',cv2.flip(image,1)),('blank',np.zeros((480,640,3),np.uint8))]
for name,img in samples:
    faces=compat.detect(img)
    scaled=cv2.resize(img,(320,320))
    _,expected=native.detect(scaled)
    expected=np.empty((0,15),np.float32) if expected is None else expected.copy()
    expected[:,[0,2,4,6,8,10,12]]*=img.shape[1]/320
    expected[:,[1,3,5,7,9,11,13]]*=img.shape[0]/320
    assert faces.shape==expected.shape,(name,faces.shape,expected.shape)
    difference=float(np.max(np.abs(faces-expected))) if faces.size else 0.
    assert difference<.001,(name,difference)
    row={'name':name,'faces':len(faces),'max_detection_abs_error':difference}
    if len(faces):
        crop=recognizer.align_crop(img,faces[0])
        native_crop=native_sf.alignCrop(img,faces[0])
        pixels=np.abs(crop.astype(np.int16)-native_crop.astype(np.int16))
        assert pixels.mean()<.01 and pixels.max()<=8,(name,pixels.mean(),pixels.max())
        a=recognizer.feature(crop);b=native_sf.feature(native_crop).reshape(-1)
        cosine=recognizer.match(a,b)
        assert cosine>.99999,(name,cosine)
        row.update(crop_mean_abs_error=float(pixels.mean()),crop_max_abs_error=int(pixels.max()),embedding_cosine=cosine)
    result['tests'].append(row)
for name,func in [('invalid_image',lambda:compat.detect(np.zeros((5,5),np.uint8))),('degenerate_landmarks',lambda:recognizer.align_crop(image,np.zeros(15))),('zero_embedding',lambda:recognizer.match(np.zeros(128),np.ones(128)))]:
    try:func()
    except ValueError:result['tests'].append({'name':name,'rejected':True})
    else:raise AssertionError(name+' was accepted')
faces=compat.detect(image);crop=recognizer.align_crop(image,faces[0]);feature=recognizer.feature(crop)
np.savez(ROOT/'reference/host_reference.npz',faces=faces,crop=crop,feature=feature)
result.update(passed=True,model_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'models').glob('*.onnx')})
(ROOT/'reference/verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
