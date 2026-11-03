"""Generic image-language inference has been removed from the product."""
VISUAL_MODE = 'board_detection_tracking_identity'
SEMANTIC_VISION_ENABLED = False
RETIRED_VISUAL_REPLY = '通用画面问答已经关闭。目前视觉使用板端的人员检测、跟踪和人脸识别，不能据此判断任意物品或场景内容。'

def visual_status():
    return {'version':1,'mode':VISUAL_MODE,'semantic_model_enabled':False,
            'image_upload_enabled':False,'detector_owner':'board',
            'historical_observations_preserved':True,
            'structured_visual_timeline_deployed':False}
