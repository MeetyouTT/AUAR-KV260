"""Add manual pan controls to the existing GTK shell without editing its source."""
import time
from board.motion.input_freshness import InputFreshness


def stage_type(base, factory):
    class PanStage(base):
        def __init__(self, *args, **kwargs):
            self.pan = factory()
            self.pan_dialog = None
            self.pan_timer = None
            self.pan_step_us = 20
            self.pan_updating = False
            self.pan_input = InputFreshness()
            self.pan_input_token = None
            self.pan_input_timer = None
            try:
                super().__init__(*args, **kwargs)
                self.pan_input_timer = self.GLib.timeout_add(50, self.pan_heartbeat)
                self.bridge.allowed_commands.update(('pan_dialog', 'pan_close', 'pan_jog', 'pan_stop', 'pan_reverse', 'pan_reconnect'))
            except BaseException:
                self.pan.close()
                raise

        def pan_heartbeat(self):
            self.pan_input.heartbeat()
            return True

        def pan_event_source(self, widget):
            event = self.Gtk.get_current_event()
            allowed = (self.Gdk.EventType.BUTTON_RELEASE, self.Gdk.EventType.TOUCH_END)
            if event is None or event.type not in allowed:
                raise ValueError('请直接点击转轴按钮')
            import gi
            gi.require_version('GdkX11', '3.0')
            from gi.repository import GdkX11
            before = time.monotonic()
            server_ms = GdkX11.x11_get_server_time(widget.get_window())
            after = time.monotonic()
            return self.pan_input.source_time(event.get_time(), server_ms, before, after)

        def activated(self, widget, data, key):
            if data.get('type') == 'pan_jog':
                try:
                    source = self.pan_event_source(widget)
                    self.pan_input_token = object()
                    data = dict(data, _pan_input=self.pan_input_token, _pan_source=source)
                except Exception as exc:
                    self.pan_input_token = None
                    if self.pan_dialog:
                        self.pan_message.set_text(str(exc))
                    return
                try:
                    return super().activated(widget, data, key)
                finally:
                    self.pan_input_token = None
            return super().activated(widget, data, key)

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
            if kind == 'pan_close':
                self.close_pan_dialog()
                return {'ok':True}
            if kind == 'pan_jog':
                token, self.pan_input_token = self.pan_input_token, None
                if token is None or data.get('_pan_input') is not token:
                    raise ValueError('请直接点击转轴按钮；远程或积压指令不执行')
                return self.pan.jog(data.get('direction'), data.get('step_us', self.pan_step_us),
                                    source_time=data['_pan_source'])
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
            state['manual_pan']['panel_open'] = self.pan_dialog is not None

        def show_page(self, page):
            if page != 'vision' and self.pan_dialog:
                self.close_pan_dialog()
            super().show_page(page)
            if self.pan_dialog:
                self.vision_insights.hide()
                self.avatar_title.set_text('转轴调节')

        def open_pan_dialog(self):
            if self.pan_dialog:
                return {'ok':True, 'message':'转轴调节已打开'}
            self.show_page('vision')
            gtk = self.Gtk
            # Keep the camera canvas unobstructed while the user adjusts it.
            # One in-window panel also keeps diagnostic coordinates in the
            # main widget tree; a separate dialog has no such translation.
            dialog = gtk.EventBox()
            dialog.get_style_context().add_class('card')
            dialog.set_size_request(self.geometry['w'], self.geometry['h'])
            box = gtk.Box(orientation=gtk.Orientation.VERTICAL, spacing=12)
            box.set_border_width(12)
            dialog.add(box)
            inner_width = self.geometry['w']-24
            title = gtk.Label(label='转轴调节')
            box.pack_start(title, False, False, 0)
            self.pan_position = gtk.Label(label='正在读取当前位置…')
            self.pan_position.set_size_request(inner_width, 42)
            self.pan_position.get_style_context().add_class('insight_value')
            box.pack_start(self.pan_position, False, False, 0)
            self.pan_message = gtk.Label(label='每次点击只执行一次点动。')
            self.pan_message.set_line_wrap(True)
            self.pan_message.set_max_width_chars(22)
            self.pan_message.set_ellipsize(3)
            self.pan_message.set_lines(3)
            self.pan_message.set_size_request(inner_width, 72)
            box.pack_start(self.pan_message, False, False, 0)
            choices = gtk.Box(spacing=8)
            self.pan_step = gtk.ComboBoxText()
            self.pan_step.append('20', '普通点动 · 20 µs')
            self.pan_step.append('5', '精细调整 · 5 µs')
            self.pan_step.set_active_id(str(self.pan_step_us))
            self.pan_step.set_size_request(198, 52)
            self.pan_step.connect('changed', lambda widget:setattr(self, 'pan_step_us', int(widget.get_active_id())))
            choices.pack_start(self.pan_step, True, True, 0)
            self.pan_reverse = gtk.CheckButton(label='左右方向互换')
            self.pan_reverse.set_size_request(180, 52)
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
                button.set_size_request((inner_width-24)//3, 64)
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
            footer = gtk.Box(spacing=12)
            self.pan_reconnect = gtk.Button(label='重新连接')
            self.pan_reconnect.set_size_request(180, 52)
            self.pan_reconnect.connect('clicked', lambda *_:self.native({'type':'pan_reconnect'}))
            footer.pack_start(self.pan_reconnect, True, True, 0)
            self.pan_return = gtk.Button(label='返回视觉解读')
            self.pan_return.set_size_request(180, 52)
            self.pan_return.connect('clicked', lambda *_:self.close_pan_dialog())
            footer.pack_start(self.pan_return, True, True, 0)
            box.pack_start(footer, False, False, 0)
            self.fixed.put(dialog, self.geometry['x'], self.geometry['y'])
            self.pan_dialog = dialog
            self.vision_insights.hide()
            self.avatar_title.set_text('转轴调节')
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
                message += '。每次点击只执行一次点动。'
            self.pan_message.set_text(message)
            self.pan_message.set_tooltip_text(message)
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
                for key, button in self.pan_buttons.items():
                    if self.controls.get('pan_'+key) is button:
                        del self.controls['pan_'+key]
                dialog.destroy()
                if self.page == 'vision':
                    self.vision_insights.show()
                    self.avatar_title.set_text('视觉解读')

        def cleanup(self):
            if self.pan_input_timer:
                self.GLib.source_remove(self.pan_input_timer)
                self.pan_input_timer = None
            self.close_pan_dialog()
            self.pan.close()
            super().cleanup()

    return PanStage
