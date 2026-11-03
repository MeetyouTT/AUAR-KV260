"""Add manual pan controls to the existing GTK shell without editing its source."""
def stage_type(base, factory):
    class PanStage(base):
        def __init__(self, *args, **kwargs):
            self.pan = factory()
            self.pan_dialog = None
            self.pan_timer = None
            self.pan_step_us = 20
            self.pan_updating = False
            try:
                super().__init__(*args, **kwargs)
                self.bridge.allowed_commands.update(('pan_dialog', 'pan_jog', 'pan_stop', 'pan_reverse', 'pan_reconnect'))
            except BaseException:
                self.pan.close()
                raise

        def build_window(self, windowed):
            super().build_window(windowed)
            button = self.controls['vision_settings']
            button.set_label('转轴调节')
            button.disconnect_by_func(self.activated)
            button.connect('clicked', self.activated, {'type':'pan_dialog'}, 'pan_open')
            self.controls['pan_open'] = button

        def command(self, data):
            kind = data.get('type')
            if kind == 'pan_dialog':
                return self.open_pan_dialog()
            if kind == 'pan_jog':
                return self.pan.jog(data.get('direction'), data.get('step_us', self.pan_step_us))
            if kind == 'pan_stop':
                return self.pan.stop()
            if kind == 'pan_reverse':
                return self.pan.reverse()
            if kind == 'pan_reconnect':
                return self.pan.reconnect()
            return super().command(data)

        def refresh_runtime(self, state, settings_text):
            super().refresh_runtime(state, settings_text)
            state['manual_pan'] = self.pan.read()

        def open_pan_dialog(self):
            if self.pan_dialog:
                self.pan_dialog.present()
                return {'ok':True, 'message':'转轴调节已打开'}
            gtk = self.Gtk
            dialog = gtk.Dialog(title='转轴调节', transient_for=self.window, modal=True)
            dialog.set_decorated(False)
            dialog.set_resizable(False)
            dialog.set_border_width(16)
            box = dialog.get_content_area()
            box.set_spacing(12)
            title = gtk.Label(label='转轴调节 · 中位待确认')
            box.pack_start(title, False, False, 0)
            self.pan_position = gtk.Label(label='正在读取当前位置…')
            self.pan_position.set_size_request(540, 38)
            self.pan_position.get_style_context().add_class('insight_value')
            box.pack_start(self.pan_position, False, False, 0)
            self.pan_message = gtk.Label(label='点动到正前方后，把位置数值告诉我。')
            self.pan_message.set_line_wrap(True)
            self.pan_message.set_max_width_chars(32)
            self.pan_message.set_size_request(540, 48)
            box.pack_start(self.pan_message, False, False, 0)
            choices = gtk.Box(spacing=12)
            self.pan_step = gtk.ComboBoxText()
            self.pan_step.append('20', '普通点动 · 20 µs')
            self.pan_step.append('5', '精细调整 · 5 µs')
            self.pan_step.set_active_id(str(self.pan_step_us))
            self.pan_step.set_size_request(254, 52)
            self.pan_step.connect('changed', lambda widget:setattr(self, 'pan_step_us', int(widget.get_active_id())))
            choices.pack_start(self.pan_step, True, True, 0)
            self.pan_reverse = gtk.CheckButton(label='左右方向互换')
            self.pan_reverse.set_size_request(240, 52)
            def reverse(widget):
                if not self.pan_updating:
                    result = self.native({'type':'pan_reverse'})
                    if not result.get('ok'):
                        self.pan_message.set_text(result.get('error','方向切换失败'))
            self.pan_reverse.connect('toggled', reverse)
            choices.pack_start(self.pan_reverse, True, True, 0)
            box.pack_start(choices, False, False, 0)
            actions = gtk.Box(spacing=12)
            self.pan_buttons = {}
            for key, label, data in [('left','← 左转',{'type':'pan_jog','direction':'left'}),
                                     ('stop','停止',{'type':'pan_stop'}),
                                     ('right','右转 →',{'type':'pan_jog','direction':'right'})]:
                button = gtk.Button(label=label)
                button.set_size_request(172, 64)
                button.set_can_focus(False)
                button.add_events(self.Gdk.EventMask.TOUCH_MASK)
                button.connect('touch-event', self.observe_touch, label)
                button.connect('clicked', self.activated, data, 'pan_'+key)
                if key == 'stop':
                    button.get_style_context().add_class('danger')
                actions.pack_start(button, True, True, 0)
                self.pan_buttons[key] = button
                self.controls['pan_'+key] = button
            box.pack_start(actions, False, False, 0)
            self.pan_reconnect = dialog.add_button('重新连接', 101)
            self.pan_reconnect.set_size_request(150, 52)
            dialog.add_button('返回', gtk.ResponseType.CLOSE).set_size_request(150, 52)
            def respond(widget, response):
                if response == 101:
                    self.native({'type':'pan_reconnect'})
                else:
                    self.close_pan_dialog()
            dialog.connect('response', respond)
            dialog.connect('delete-event', lambda *unused:(self.close_pan_dialog() or True))
            self.pan_dialog = dialog
            dialog.show_all()
            self.refresh_pan_dialog()
            self.pan_timer = self.GLib.timeout_add(100, self.refresh_pan_dialog)
            return {'ok':True, 'message':'转轴调节已打开'}

        def refresh_pan_dialog(self):
            if not self.pan_dialog:
                return False
            value = self.pan.read()
            pulse = value.get('pulse_us')
            self.pan_position.set_text('当前位置  '+(str(pulse)+' µs' if pulse is not None else '待读取'))
            message = value.get('error') or value.get('message','')
            if value['state'] == 'READY':
                message += '。调到正前方后，把数值告诉我。'
            self.pan_message.set_text(message)
            ready = value['state'] == 'READY'
            for key in ('left', 'right'):
                sign = value['left_sign'] * (1 if key == 'left' else -1)
                target = pulse + sign*self.pan_step_us if pulse is not None else None
                self.pan_buttons[key].set_sensitive(ready and target is not None and value['minimum_us'] <= target <= value['maximum_us'])
            self.pan_buttons['stop'].set_sensitive(value['state'] in ('READY', 'MOVING', 'STOPPING'))
            self.pan_step.set_sensitive(ready)
            self.pan_reconnect.set_sensitive(value['state'] in ('FAULT','UNAVAILABLE'))
            self.pan_updating = True
            try:
                self.pan_reverse.set_active(value['left_sign'] == 1)
                self.pan_reverse.set_sensitive(ready)
            finally:
                self.pan_updating = False
            return True

        def close_pan_dialog(self):
            self.pan.stop()
            if self.pan_timer:
                self.GLib.source_remove(self.pan_timer)
                self.pan_timer = None
            if self.pan_dialog:
                dialog, self.pan_dialog = self.pan_dialog, None
                dialog.destroy()

        def cleanup(self):
            self.close_pan_dialog()
            self.pan.close()
            super().cleanup()

    return PanStage
