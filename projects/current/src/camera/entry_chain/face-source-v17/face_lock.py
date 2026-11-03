"""Keep face inference publication independent of the camera's shared lock."""
import threading


def install(service_type=None):
    if service_type is None:
        from board.identity.face_targets import FaceTargetService
        service_type=FaceTargetService
    if getattr(service_type,'_edge_independent_face_lock',False):
        return
    original=service_type.__init__

    def initialize(self,*args,**kwargs):
        kwargs['lock']=threading.RLock()
        original(self,*args,**kwargs)

    service_type.__init__=initialize
    service_type._edge_independent_face_lock=True
