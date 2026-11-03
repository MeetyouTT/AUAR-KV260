"""Compatibility stub for the retired periodic image-language uploader."""
class DeviceObserver:
    def __init__(self,boot,*,interval=15.,host='192.168.50.1'):
        if not 10<=interval<=300:raise ValueError('Bound observation cadence')
        self.boot=boot;self.interval=interval;self.host=host
        self.error='';self.sent=0;self.last_sent=None
    @property
    def enabled(self):return False
    @enabled.setter
    def enabled(self,value):pass
    def run(self):return
    def public(self):
        return {'enabled':False,'interval_seconds':self.interval,'sent':0,'error':'',
                'last_sent_age_seconds':None,'raw_image_storage':False,
                'mode':'board_detection_tracking_identity','image_upload_enabled':False,
                'retired_reason':'semantic_vision_removed',
                'structured_visual_timeline_deployed':False}
    def close(self):return
