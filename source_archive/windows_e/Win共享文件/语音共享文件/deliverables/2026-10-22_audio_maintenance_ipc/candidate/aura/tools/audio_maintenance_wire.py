"""Private pipe protocol. The parent owner must hold capture/intent admission."""
import re

HEX32=re.compile(r'[0-9a-f]{32}\Z')


class WorkerMaintenanceProtocol:
    def __init__(self,engine,instance):
        if not isinstance(instance,str) or not HEX32.fullmatch(instance):
            raise ValueError('Explicit worker instance required')
        self.engine,self.instance=engine,instance

    def stamp(self,value):
        return dict(value,worker_instance=self.instance,pipeline_epoch=self.engine.pipeline_epoch,
                    token=self.engine.token)

    def command(self,message,*,commands_pending):
        if message.get('worker_instance')!=self.instance:
            return False,None
        if message.get('type')!='recover_idle':
            return self.engine.command(message),None
        request=message.get('request_id');expected=message.get('expected_token');token=message.get('token')
        valid=(set(message)=={'type','worker_instance','request_id','expected_token','token'}
            and isinstance(request,str) and HEX32.fullmatch(request)
            and type(expected) is int and type(token) is int and expected>=0 and token==expected+1
            and commands_pending is False)
        accepted=bool(valid and self.engine.request_idle_maintenance(request_id=request,
            expected_token=expected,new_token=token,controller_idle=True,capture_idle=True,
            reference_idle=True,commands_pending=False))
        ack={'kind':'maintenance_ack','worker_instance':self.instance,
             'request_id':request if isinstance(request,str) and HEX32.fullmatch(request) else None,
             'expected_token':expected if type(expected) is int else None,
             'requested_token':token if type(token) is int else None,
             'engine_token':self.engine.token,'pipeline_epoch':self.engine.pipeline_epoch,
             'accepted':accepted}
        return accepted,ack
