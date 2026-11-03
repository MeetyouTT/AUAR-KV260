"""Physical board-local profile selection; credentials stay in this process.

There is no Windows control call or grant-file fallback. The operator must
explicitly choose an existing profile, or consent to create one, then supply
the configured local control credential. The entry is masked and never logged.
"""


def select_local_profile(runtime, *, operator_key, profile_id=None, name=None, consent=False):
    if runtime.profiles is None:
        raise PermissionError('Board-local profile control is unavailable')
    runtime.access.authenticate(operator_key)
    if profile_id is None:
        if consent is not True:
            raise PermissionError('Creating a profile requires explicit local consent')
        profile_id = runtime.store.create_profile(name, consent=True)
    elif name is not None or consent is not False:
        raise ValueError('Existing profile selection must not also create a profile')
    runtime.store.require_profile(profile_id)
    rows = runtime.store.profiles()
    selected = next(row for row in rows if row['id'] == profile_id)
    wire = runtime.profiles.issue(profile_id, operator_key, profile_name=selected['name'])
    try:
        runtime.jobs.select_profile(wire)
    except BaseException:
        runtime.profiles.release(runtime.profiles.resolve(wire, runtime.boot_id))
        raise
    return dict(mode='personal', profile_id=profile_id)


def local_board_profile_dialog(stage):
    state = stage.controller.public()
    if (state.get('phase') != 'IDLE' or state.get('playing')
            or state.get('handsfree_dialogue', {}).get('enabled')
            or state.get('local_recording', {}).get('can_stop')):
        raise ValueError('请先暂停对话，再切换个人档案')
    runtime = stage.board_business.runtime
    Gtk = stage.Gtk
    dialog = Gtk.Dialog(title='个人长期记忆', transient_for=stage.window, modal=True)
    content = dialog.get_content_area()
    content.set_spacing(12)
    configured = runtime.profiles is not None and runtime.access.health()['configured']
    content.add(Gtk.Label(label='选择板端本地档案。只有明确授权后，才读取该档案的长期记忆。'))
    options = Gtk.ComboBoxText()
    rows = runtime.store.profiles()
    for row in rows:
        options.append(row['id'], row['name'])
    if rows:
        options.set_active(0)
    content.add(options)
    content.add(Gtk.Label(label='新建档案称呼（仅新建时填写）'))
    name = Gtk.Entry(); name.set_max_length(40); content.add(name)
    consent = Gtk.CheckButton(label='我同意在板端保存这个个人档案和明确记忆')
    content.add(consent)
    content.add(Gtk.Label(label='板端本地授权密钥' if configured else '尚未配置板端本地授权，请先完成本地配置。'))
    key = Gtk.Entry(); key.set_visibility(False); key.set_max_length(64); content.add(key)
    for label, response in [('返回', Gtk.ResponseType.CANCEL), ('切回访客', Gtk.ResponseType.NO),
                            ('使用所选档案', Gtk.ResponseType.YES), ('新建并使用', Gtk.ResponseType.APPLY)]:
        button = dialog.add_button(label, response)
        button.set_size_request(160, 54)
        if response in (Gtk.ResponseType.YES, Gtk.ResponseType.APPLY):
            button.set_sensitive(configured and (bool(rows) or response == Gtk.ResponseType.APPLY))
    dialog.set_default_response(Gtk.ResponseType.CANCEL)
    dialog.show_all()
    try:
        response = dialog.run()
        if response == Gtk.ResponseType.NO:
            runtime.jobs.select_profile(None)
            return {'ok': True, 'message': '已切回访客，新对话已开始'}
        if response == Gtk.ResponseType.YES:
            select_local_profile(runtime, operator_key=key.get_text(), profile_id=options.get_active_id())
            return {'ok': True, 'message': '已切换个人长期记忆'}
        if response == Gtk.ResponseType.APPLY:
            select_local_profile(runtime, operator_key=key.get_text(), name=name.get_text(), consent=consent.get_active())
            return {'ok': True, 'message': '已在板端新建并选择个人档案'}
        return {'ok': True, 'message': '已返回'}
    finally:
        key.set_text('')
        dialog.destroy()
