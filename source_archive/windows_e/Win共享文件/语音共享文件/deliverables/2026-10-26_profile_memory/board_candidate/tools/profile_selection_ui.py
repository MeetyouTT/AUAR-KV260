"""A local dialog activates a delivered grant only after the user's click."""
from pathlib import Path


def profile_dialog(stage):
    status=stage.controller.public()
    if (status.get('phase')!='IDLE' or status.get('playing')
            or status.get('handsfree_dialogue',{}).get('enabled')
            or status.get('local_recording',{}).get('can_stop')):
        raise ValueError('请先暂停对话，再切换个人档案')
    from common.profile_selection import read_selection
    value=None
    try:value=read_selection(Path.home()/'.local/share/aura/profile-selection.json',stage.board_boot_id)
    except (OSError,ValueError,PermissionError):pass
    Gtk=stage.Gtk
    dialog=Gtk.Dialog(title='个人长期记忆',transient_for=stage.window,modal=True)
    active=getattr(stage.transcriber,'profile_selection',None)
    text=('当前：个人记忆。' if active else '当前：访客模式。')
    text+=('\n可选择已授权档案：'+str(value.get('profile_name','个人档案'))+
           '\n仅在本次授权有效期内读取长期记忆。' if value else '\n尚无本次启动的档案授权，请先在Windows授权。')
    dialog.get_content_area().add(Gtk.Label(label=text))
    for label,response in [('返回',Gtk.ResponseType.CANCEL),('切回访客',Gtk.ResponseType.NO),('使用授权档案',Gtk.ResponseType.YES)]:
        button=dialog.add_button(label,response);button.set_size_request(160,54)
        if response==Gtk.ResponseType.YES:button.set_sensitive(value is not None)
    dialog.set_default_response(Gtk.ResponseType.CANCEL)
    dialog.show_all();response=dialog.run();dialog.destroy()
    if response not in (Gtk.ResponseType.YES,Gtk.ResponseType.NO):return {'ok':True,'message':'已返回'}
    if response==Gtk.ResponseType.YES and value is None:raise ValueError('尚无有效档案授权')
    stage.transcriber.select_profile(value if response==Gtk.ResponseType.YES else None)
    return {'ok':True,'message':'已切换个人长期记忆' if response==Gtk.ResponseType.YES else '已切回访客，新对话已开始'}
