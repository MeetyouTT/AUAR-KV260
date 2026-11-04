"""The AURA dual-device monitor. All Tk calls stay on the main thread."""
from collections import deque
import queue
import threading
import time
import tkinter as tk
from tkinter import font, ttk, messagebox

from runtime_board_monitor import BoardSampler, ROLE_NAMES, board_tasks


BG = '#101927'
PANEL = '#192638'
SURFACE = '#203047'
LINE = '#34465c'
TEXT = '#f1f5f9'
MUTED = '#a9bbce'
BLUE = '#91c8ff'
MINT = '#6cddc1'
GOLD = '#ffd18a'
VIOLET = '#c0b6ff'
FONT = 'Microsoft YaHei UI'
PC_ROLES = {'host': '模型宿主', 'llm': '27B 语言模型', 'tts': 'OmniVoice', 'portrait': '形象服务',
            'other': '其他 Ollama', 'legacy': '早期业务', 'project': '其他项目进程', 'monitor': '观测台'}
WORDS = {
    'IDLE': '待机', 'THINKING': '生成中', 'SPEAKING': '播报中', 'PAUSED': '已暂停',
    'WAITING_SPEECH': '等待说话', 'CHECKING_SPEECH': '检查语音', 'CONVERSATION': '对话中',
    'GENERATING': '生成中', 'COOLDOWN': '轮次间隔', 'WAITING_FOR_FACE': '等待人脸',
    'MONITORING': '监测中', 'FOLLOWING': '跟随中', 'CONFIRMING': '确认目标',
    'HOLD_AT_LIMIT': '边界保持', 'BRAKING': '减速中', 'PLAYING': '播放中',
    'CANCELLED': '已取消', 'IDLE_READY': '设备就绪', 'READY': '就绪',
    'SAFE_ZONE_HOLD': '目标在范围内', 'SOURCE_EXPIRED': '等待新的人脸画面',
    'headroom_available': '显存余量充足', 'insufficient_headroom': '等待显存余量',
    'same_phase_active': '同类计算占用中', 'serialized_peak': '等待前一阶段结束',
    'adaptive': '自适应准入', 'serial': '串行准入', 'Running': '运行中',
    'Stopped': '已停止', 'active': '已激活', 'inactive': '未激活',
    'failed': '失败', 'running': '运行中', 'exited': '已退出', 'dead': '已停止',
    'activating': '启动中', 'deactivating': '停止中', 'Auto': '自动', 'Manual': '手动',
    'Disabled': '已禁用', 'loaded': '已加载', 'not-found': '未找到',
}


def word(value):
    return WORDS.get(value, value) if value not in (None, '') else '—'


def num(value, suffix='', digits=0):
    return '—' if value is None else f'{value:,.{digits}f}{suffix}'


def size(mib):
    if mib is None:
        return '—'
    return f'{mib / 1024:.2f} GiB' if mib >= 1024 else f'{mib:,.0f} MiB'


def byte_size(value):
    return size(value / 1048576) if value is not None else '—'


def yes(value, positive, negative):
    return positive if value is True else negative if value is False else '待观测'


def label(parent, text='', points=10, color=TEXT, bold=False, bg=None, **options):
    return tk.Label(parent, text=text, font=(FONT, points, 'bold' if bold else 'normal'), fg=color,
                    bg=bg or parent.cget('bg'), anchor='w', justify='left', **options)


class GridTable(ttk.Frame):
    def __init__(self, parent, columns, scale):
        super().__init__(parent)
        self.columns = [key for key, _, _, _ in columns]
        self.labels = {key: title for key, title, _, _ in columns}
        self.sort_key = None
        self.reverse = False
        self.rows = {}
        self.tree = ttk.Treeview(self, columns=self.columns, show='headings', selectmode='browse', height=5)
        for key, title, width, stretch in columns:
            self.tree.heading(key, text=title, command=lambda k=key: self.sort(k), anchor='w')
            self.tree.column(key, width=round(width * scale), minwidth=round(min(width, 56) * scale),
                             stretch=stretch, anchor='w')
        vert = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        horiz = ttk.Scrollbar(self, orient='horizontal', command=self.tree.xview)
        def scroll(bar, first, last):
            bar.set(first, last)
            needed = float(first) > .00001 or float(last) < .99999
            if needed and not bar.winfo_manager():
                bar.grid()
            elif not needed and bar.winfo_manager():
                bar.grid_remove()
        self.tree.configure(yscrollcommand=lambda a, b: scroll(vert, a, b),
                            xscrollcommand=lambda a, b: scroll(horiz, a, b))
        self.tree.grid(row=0, column=0, sticky='nsew')
        vert.grid(row=0, column=1, sticky='ns')
        horiz.grid(row=1, column=0, sticky='ew')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.tree.tag_configure('even', background=PANEL)
        self.tree.tag_configure('odd', background='#1d2b3d')

    def sort(self, key):
        self.reverse = not self.reverse if self.sort_key == key else key in ('cpu', 'rss', 'gpu', 'vram', 'threads')
        self.sort_key = key
        for col in self.columns:
            arrow = (' ▼' if self.reverse else ' ▲') if key == col else ''
            self.tree.heading(col, text=self.labels[col] + arrow)
        self.fill(list(self.rows.values()))

    def fill(self, rows):
        if self.sort_key:
            col = self.sort_key
            def sort_value(row):
                return row.get('_sort', {}).get(col, row.get(col))
            known = [row for row in rows if sort_value(row) not in (None, '—', '共享')]
            missing = [row for row in rows if sort_value(row) in (None, '—', '共享')]
            def comparable(row):
                value = sort_value(row)
                return (0, value) if isinstance(value, (int, float)) else (1, str(value).casefold())
            rows = sorted(known, key=comparable, reverse=self.reverse) + missing
        saved = self.tree.get_children()
        new = {str(row['id']): row for row in rows}
        reordered = tuple(new) != saved
        removed = set(saved) - new.keys()
        if removed:
            self.tree.delete(*removed)
        for index, (iid, row) in enumerate(new.items()):
            values = tuple(str(row.get(col, '—')) for col in self.columns)
            tag = ('even',) if index % 2 == 0 else ('odd',)
            old = self.rows.get(iid)
            if old is None:
                self.tree.insert('', 'end', iid=iid, values=values, tags=tag)
            elif old != row or reordered:
                self.tree.item(iid, values=values, tags=tag)
        if reordered:
            self.tree.set_children('', *new)
        self.rows = new

    def selected(self):
        selection = self.tree.selection()
        return self.rows.get(selection[0]) if selection else None


class Tile(tk.Frame):
    def __init__(self, parent, tag, title, color, scale):
        super().__init__(parent, bg=PANEL, padx=round(12 * scale), pady=round(7 * scale),
                         highlightthickness=1, highlightbackground=LINE)
        top = tk.Frame(self, bg=PANEL)
        top.pack(fill='x')
        label(top, tag, 8, color, True).pack(side='left')
        label(top, title, 10, TEXT, True).pack(side='left', padx=(round(6 * scale), 0))
        self.value = label(self, '待采样', 11, color, True)
        self.value.pack(fill='x', pady=(3, 0))
        self.note = label(self, '', 9, MUTED)
        self.note.pack(fill='x')
        self.bind('<Configure>', lambda event: self.note.configure(wraplength=max(70, event.width - round(28 * scale))))

    def set(self, value, note='', active=False):
        self.value.configure(text=value)
        self.note.configure(text=note)
        self.configure(highlightbackground=GOLD if active else LINE)


class Trend(tk.Frame):
    def __init__(self, parent, title, legend, color, scale):
        super().__init__(parent, bg=PANEL, padx=round(12 * scale), pady=round(6 * scale),
                         highlightthickness=1, highlightbackground=LINE)
        self.header = tk.Frame(self, bg=PANEL)
        self.header.pack(fill='x')
        label(self.header, title, 12, color, True).pack(side='left')
        label(self.header, legend, 9, MUTED).pack(side='left', padx=round(8 * scale))
        self.value = label(self, '等待采样', 11)
        self.value.pack(fill='x')
        self.graph = tk.Canvas(self, bg=PANEL, height=round(26 * scale), highlightthickness=0)
        self.graph.pack(fill='x')
        self.history = deque(maxlen=90)
        self.color = color
        self.graph.bind('<Configure>', lambda _: self.draw())

    def update_data(self, moment, first, second, summary):
        if moment and self.history and moment == self.history[-1][0]:
            return
        self.value.configure(text=summary)
        if moment:
            self.history.append((moment, first, second))
        self.draw()

    def draw(self):
        c = self.graph
        c.delete('all')
        width, height = c.winfo_width(), c.winfo_height()
        if width < 10 or height < 8:
            return
        for ratio in (0, .5, 1):
            y = 2 + (height - 4) * ratio
            c.create_line(0, y, width, y, fill=LINE, dash=(3, 5))
        if len(self.history) < 2:
            return
        last = self.history[-1][0]
        for field, color in ((1, BLUE), (2, self.color)):
            segment = []
            previous = None
            for sample in self.history:
                age, value = last - sample[0], sample[field]
                if age > 60:
                    continue
                if value is None or (previous is not None and sample[0] - previous > 12):
                    if len(segment) >= 4:
                        c.create_line(*segment, fill=color, width=2)
                    segment = []
                if value is not None:
                    segment.extend((width * (1 - age / 60), 2 + (height - 4) * (1 - min(100, max(0, value)) / 100)))
                previous = sample[0]
            if len(segment) >= 4:
                c.create_line(*segment, fill=color, width=2)


class Dashboard:
    def __init__(self, root, args, windows_factory, capture_window, title):
        self.root, self.args, self.capture_window = root, args, capture_window
        self.scale = min(2.5, max(.85, root.winfo_fpixels('1i') / 96))
        self.stop = threading.Event()
        self.inbox = queue.Queue()
        self.latest = {'win': {}, 'board': {}}
        self.shown = self.latest.copy()
        self.paused = False
        self.full = False
        self.pc_samples = 0
        self.threads = []
        root.title(title)
        root.configure(bg=BG)
        width = min(round(1400 * self.scale), int(root.winfo_screenwidth() * .93))
        height = min(round(845 * self.scale), int(root.winfo_screenheight() * .88))
        root.geometry(f'{width}x{height}')
        root.minsize(min(width, round(800 * self.scale)), min(height, round(520 * self.scale)))
        self.styles()
        bar = tk.Frame(root, bg=BG, padx=self.px(18), pady=self.px(8))
        bar.pack(fill='x')
        label(bar, 'AURA', 17, MINT, True).pack(side='left')
        label(bar, '双端性能观测台', 16, TEXT, True).pack(side='left', padx=self.px(12))
        ttk.Button(bar, text='指标说明', command=self.help).pack(side='right', padx=3)
        self.pause_button = ttk.Button(bar, text='暂停显示', command=self.pause)
        self.pause_button.pack(side='right', padx=3)
        self.live = label(bar, '正在连接', 9, MUTED)
        self.live.pack(side='right', padx=self.px(10))
        self.footer = label(root, '正在读取电脑和 KV260 的运行数据', 9, MUTED, padx=self.px(15), pady=self.px(4))
        self.footer.pack(side='bottom', fill='x')
        page = tk.Frame(root, bg=BG, padx=self.px(14))
        page.pack(fill='both', expand=True)
        self.make_flow(page)
        body = tk.Frame(page, bg=BG)
        body.pack(fill='both', expand=True, pady=(self.px(8), 0))
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=3)
        body.rowconfigure(1, weight=2)
        twins = tk.Frame(body, bg=BG)
        twins.grid(row=0, column=0, sticky='nsew')
        twins.rowconfigure(0, weight=1)
        for col in (0, 1):
            twins.columnconfigure(col, weight=1, uniform='devices')
        left, right = tk.Frame(twins, bg=BG), tk.Frame(twins, bg=BG)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, self.px(4)))
        right.grid(row=0, column=1, sticky='nsew', padx=(self.px(4), 0))
        self.make_windows(left)
        self.make_board(right)
        inventory = tk.Frame(body, bg=BG)
        inventory.grid(row=1, column=0, sticky='nsew')
        self.make_inventory(inventory)
        root.bind('<F11>', self.fullscreen)
        root.bind('<Escape>', lambda _: self.set_fullscreen(False))
        root.protocol('WM_DELETE_WINDOW', self.close)
        for key, factory, interval in [('win', windows_factory, 2.), ('board', BoardSampler, 5.)]:
            worker = threading.Thread(target=self.collect, args=(key, factory, interval), daemon=True, name='observer-' + key)
            self.threads.append(worker)
            worker.start()
        root.after(100, self.tick)
        root.after(150, root.deiconify)
        if args.close_after:
            root.after(round(args.close_after * 1000), self.close)

    def px(self, value):
        return max(1, round(value * self.scale))

    def styles(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', background=BG, foreground=TEXT, font=(FONT, 10),
                        bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
        row_font = font.Font(root=self.root, family=FONT, size=10)
        style.configure('Treeview', background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                        rowheight=row_font.metrics('linespace') + self.px(8), borderwidth=0)
        style.map('Treeview', background=[('selected', '#315470')], foreground=[('selected', '#ffffff')])
        style.configure('Treeview.Heading', background=SURFACE, foreground=MUTED, font=(FONT, 9, 'bold'), padding=4)
        style.map('Treeview.Heading', background=[('active', '#2c4058')])
        style.configure('TButton', background=SURFACE, foreground=TEXT, padding=(7, 3))
        style.map('TButton', background=[('active', '#354b62')])
        style.configure('TCombobox', foreground='#172b40', fieldbackground='#e2e9ef', arrowcolor=TEXT)
        style.map('TCombobox', fieldbackground=[('readonly', '#e2e9ef')], foreground=[('readonly', '#172b40')])
        style.configure('TEntry', fieldbackground='#e2e9ef', foreground='#172b40')
        style.configure('TScrollbar', background=LINE, troughcolor=BG, arrowsize=self.px(11), arrowcolor=MUTED)

    def heading(self, parent, title, caption=''):
        bar = tk.Frame(parent, bg=BG)
        bar.pack(fill='x', pady=(self.px(4), self.px(5)))
        label(bar, title, 12, TEXT, True).pack(side='left')
        if caption:
            label(bar, caption, 9, MUTED).pack(side='left', padx=self.px(12))
        return bar

    def tiles(self, parent, definitions, arrows=False):
        strip = tk.Frame(parent, bg=BG)
        strip.pack(fill='x')
        result = []
        for index, (tag, title, color) in enumerate(definitions):
            col = index * 2 if arrows else index
            strip.columnconfigure(col, weight=1, uniform='cards')
            card = Tile(strip, tag, title, color, self.scale)
            card.grid(row=0, column=col, sticky='nsew', padx=(0, 0 if arrows else self.px(4)))
            result.append(card)
            if arrows and index < len(definitions) - 1:
                label(strip, '›', 14, MUTED).grid(row=0, column=col + 1, padx=2)
        return result

    def make_flow(self, page):
        self.heading(page, '一次对话的路径', '工作分工与最近采样状态')
        self.flow = self.tiles(page, [('01  KV260', '收音与识别', MINT), ('02  WINDOWS', '生成回答', BLUE),
                                     ('03  KV260', '组织台词', MINT), ('04  WINDOWS', '合成语音', VIOLET),
                                     ('05  KV260', '播放与口型', MINT)], arrows=True)

    def panel(self, parent, title, legend, color, options, selected):
        trend = Trend(parent, title, legend, color, self.scale)
        trend.pack(fill='x')
        choice = tk.StringVar(value=selected)
        control = ttk.Combobox(trend.header, textvariable=choice, values=options, state='readonly', width=11)
        control.pack(side='right')
        control.bind('<<ComboboxSelected>>', lambda _: self.render())
        note = label(parent, '', 9, MUTED, pady=self.px(3))
        note.pack(side='bottom', fill='x')
        parent.bind('<Configure>', lambda event: note.configure(wraplength=max(120, event.width - self.px(10))))
        holder = tk.Frame(parent, bg=PANEL)
        holder.pack(fill='both', expand=True)
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)
        return trend, choice, note, holder

    def make_windows(self, parent):
        self.win_trend, self.model_view, self.model_explanation, holder = self.panel(
            parent, 'Windows 模型电脑', '蓝 CPU   紫 GPU · 60 秒', VIOLET,
            ['模型概览', '27B 对话', '语音合成', 'GPU 调度', '请求宿主', '项目进程组'],
            '27B 对话' if self.args.view == 'windows' else '模型概览')
        self.win_summary = GridTable(holder, [('name', '模型与服务', 110, False), ('state', '当前状态', 116, False),
                                    ('detail', '参数与实测', 290, True)], self.scale)
        self.model_table = GridTable(holder, [('name', '模型指标', 155, False), ('value', '观测值', 280, True)], self.scale)
        self.win_table = GridTable(holder, [('name', '进程组', 132, True), ('state', '状态', 107, True),
            ('cpu', 'CPU', 55, False), ('rss', '工作集', 78, False), ('gpu', 'GPU', 52, False),
            ('vram', '专用显存', 85, False)], self.scale)
        self.win_table.tree.bind('<<TreeviewSelect>>', lambda _: self.show_win_selection())
        for table in (self.win_table, self.model_table, self.win_summary):
            table.grid(row=0, column=0, sticky='nsew')

    def make_board(self, parent):
        self.board_trend, self.board_view, self.board_note, holder = self.panel(
            parent, 'KV260 玩偶板卡', '蓝 CPU   绿内存 · 60 秒', MINT,
            ['板端概览', '功能与进程组'], '功能与进程组' if self.args.view == 'board' else '板端概览')
        self.board_summary = GridTable(holder, [('name', '板端功能', 105, False), ('state', '当前状态', 112, False),
                                      ('detail', '参数与实测', 290, True)], self.scale)
        self.board_table = GridTable(holder, [('name', '任务', 141, True), ('state', '状态', 85, False),
            ('cpu', 'CPU', 56, False), ('rss', '常驻内存', 75, False), ('detail', '工作情况', 202, True)], self.scale)
        self.board_table.tree.bind('<<TreeviewSelect>>', lambda _: self.show_board_selection())
        for table in (self.board_table, self.board_summary):
            table.grid(row=0, column=0, sticky='nsew')

    def make_inventory(self, page):
        bar = self.heading(page, '双端后台清单')
        self.kind = tk.StringVar(value='进程')
        self.device = tk.StringVar(value='两端')
        self.scope = tk.StringVar(value='全部')
        self.search = tk.StringVar()
        for var, values, width in ((self.kind, ['进程', '服务'], 6), (self.device, ['两端', 'Windows', 'KV260'], 9),
                                   (self.scope, ['全部', '项目及支撑'], 10)):
            box = ttk.Combobox(bar, textvariable=var, values=values, state='readonly', width=width)
            box.pack(side='left', padx=(self.px(7), 0))
            box.bind('<<ComboboxSelected>>', lambda _: self.render())
        label(bar, '搜索', 9, MUTED).pack(side='left', padx=(self.px(12), 3))
        ttk.Entry(bar, textvariable=self.search, width=18).pack(side='left')
        self.search.trace_add('write', lambda *_: self.render())
        self.inventory_note = label(page, '', 9, MUTED, pady=3)
        self.inventory_note.pack(fill='x')
        self.process_table = GridTable(page, [('device', '端', 77, False), ('name', '进程名', 160, True),
            ('pid', 'PID', 69, False), ('ppid', '父 PID', 69, False), ('role', '归属', 140, True),
            ('threads', '线程', 56, False), ('cpu', 'CPU', 70, False), ('rss', '常驻内存', 94, False),
            ('gpu', 'GPU', 64, False), ('vram', '专用显存', 95, False)], self.scale)
        self.service_table = GridTable(page, [('device', '端', 85, False), ('name', '服务名', 220, True),
            ('info', '说明 / 载入状态', 230, True), ('state', '当前状态', 115, False),
            ('mode', '启动方式 / 子状态', 137, False), ('pid', '采样 PID', 150, True)], self.scale)
        self.process_table.sort_key, self.process_table.reverse = 'cpu', True
        self.process_table.tree.heading('cpu', text='CPU ▼')
        self.process_table.pack(fill='both', expand=True)


    def render(self):
        if not hasattr(self, 'inventory_note'):
            return
        win, board = self.shown['win'], self.shown['board']
        connected = board.get('online') is True
        self.live.configure(text=('暂停显示' if self.paused else '实时采样') + '   ·   Windows ' +
                            ('在线' if 'tasks' in win else '待观测') + '   ·   KV260 ' +
                            ('在线' if connected else '未连接' if board else '连接中'),
                            fg=GOLD if self.paused or board and not connected else MINT)
        win_stamp = str(win.get('local_time') or '')[11:19] or '等待数据'
        board_stamp = str(board.get('local_time') or '')[11:19] or '等待数据'
        self.footer.configure(text=f'Windows  {win_stamp}  ·  2 秒     KV260  {board_stamp}  ·  5 秒     ' +
                              (board.get('error') or win.get('error') or '只读采样') + '       F11 全屏')
        self.update_trends(win, board)
        self.draw_flow(win, board)
        self.draw_windows(win, board)
        self.draw_board(board)
        self.draw_inventory(win, board)

    @staticmethod
    def phases(win):
        model = win.get('model_detail', {})
        active = win.get('gpu_active', {})
        llm = '推理中' if active.get('llm') else yes(model.get('resident'), '模型已驻留', '模型未驻留')
        tts = '合成中' if model.get('tts_request') or active.get('tts') else yes(model.get('tts_ready'), '模型就绪', '尚未就绪')
        return llm, tts

    def draw_flow(self, win, board):
        gui = board.get('gui', {})
        listen = gui.get('listening', {})
        dialogue = gui.get('dialogue', {})
        model, leases = win.get('model_detail', {}), win.get('gpu_active', {})
        llm, tts = self.phases(win)
        playing = gui.get('playing')
        pending = dialogue.get('pending')
        compiling = '对话任务进行中' if pending else '等待下一轮' if pending is not None or gui.get('phase') == 'IDLE' else '待观测'
        flow = [
            (word(listen.get('state')), '麦克风与 Paraformer', listen.get('microphone_open')),
            (llm, 'Ollama · 27B 文本推理', leases.get('llm')),
            (compiling, '板端解析回复并分段请求语音', pending),
            (tts, 'OmniVoice · ' + num(model.get('steps'), ' 步'), model.get('tts_request') or leases.get('tts')),
            (yes(playing, '正在播报', '等待播放'), '24 kHz 音频与角色动画', playing),
        ]
        for card, (value, detail, active) in zip(self.flow, flow):
            card.set(value, detail, bool(active))

    def update_trends(self, win, board):
        gpu = next(iter(win.get('nvidia', {}).get('cards', [])), {})
        self.win_trend.update_data(win.get('monotonic'), win.get('system_cpu_pct'), gpu.get('gpu_pct'),
            'CPU ' + num(win.get('system_cpu_pct'), '%', 1) + '    GPU ' + num(gpu.get('gpu_pct'), '%') +
            '    显存 ' + size(gpu.get('memory_used_mib')) + ' / ' + size(gpu.get('memory_total_mib')) +
            '\n内存 ' + size(win.get('ram_used_mib')) + ' / ' + size(win.get('ram_total_mib')))
        avail, total = (board.get('memory', {}).get(k) for k in ('MemAvailable', 'MemTotal'))
        used = total - avail if total is not None and avail is not None else None
        self.board_trend.update_data(board.get('received_at'), board.get('system_cpu_pct'), used / total * 100 if total and used is not None else None,
            'CPU ' + num(board.get('system_cpu_pct'), '%', 1) + '    内存 ' + size(used) + ' / ' + size(total) +
            '\n相机 ' + num(board.get('camera', {}).get('capture_hz'), ' 帧/秒', 1) + '    角色 ' +
            num(board.get('gui', {}).get('avatar', {}).get('observed_fps'), ' 帧/秒', 1))

    def show_win_selection(self):
        if self.model_view.get() == '项目进程组':
            row = self.win_table.selected()
            self.model_explanation.configure(text=row['_detail'] if row else '选择一行查看 PID、私有内存和采样覆盖。')

    def show_board_selection(self):
        if self.board_view.get() == '功能与进程组':
            row = self.board_table.selected()
            self.board_note.configure(text=row['_detail'] if row else '选择一行查看所属进程和 PID。共用进程的功能在资源列标为“共享”。')

    def draw_windows(self, win, board):
        m, active, counts = win.get('model_detail', {}), win.get('gpu_active', {}), win.get('counters', {})
        llm, tts = self.phases(win)
        gui = board.get('gui', {})
        prep = gui.get('prepare', {})
        kind = self.model_view.get()
        if kind == '模型概览':
            rows = [
                ('27B 文本生成', llm, word(m.get('parameter_size')) + '  ·  ' + word(m.get('quantization')) +
                 '  ·  ' + num(m.get('instance_context'), ' token')),
                ('模型驻留显存', byte_size(m.get('gpu_bytes')), '由 Ollama 报告  ·  ' + word(m.get('runner'))),
                ('OmniVoice 语音', tts, num(m.get('steps'), ' 步合成') + '  ·  已生成 ' + num(m.get('tts_generated'), ' 次')),
                ('GPU 调度', word(m.get('mode')), '文本占用 ' + num(active.get('llm')) + '  ·  语音占用 ' +
                 num(active.get('tts')) + '  ·  排队 ' + num(win.get('gpu_queued'))),
                ('请求宿主', yes(win.get('active'), '处理请求中', '等待请求'), '累计接收   文本 ' +
                 num(counts.get('accepted_llm')) + '  ·  语音 ' + num(counts.get('accepted_tts'))),
                ('最近轮次往返', '板端计时', '文本 ' + num(prep.get('llm_rpc_ms'), ' ms') +
                 '  ·  语音合计 ' + num(prep.get('tts_rpc_ms'), ' ms')),
            ]
            self.win_summary.fill([dict(id=name, name=name, state=state, detail=detail) for name, state, detail in rows])
            self.win_summary.tkraise()
            self.model_explanation.configure(text='27B 根据角色和近期对话逐个 token 生成回复。板端提取台词，再交给 OmniVoice 合成。')
            return
        if kind == '项目进程组':
            rows = []
            for task in win.get('tasks', []):
                rows.append(dict(id=task['id'], name=task['name'], state=task['state'], cpu=num(task['cpu_pct'], '%', 1),
                    rss=size(task['rss_mib']), gpu=num(task['gpu_pct'], '%', 1), vram=size(task['vram_mib']),
                    _sort={'cpu': task['cpu_pct'], 'rss': task['rss_mib'], 'gpu': task['gpu_pct'], 'vram': task['vram_mib']},
                    _detail=task['description'] + '  ·  PID ' + (', '.join(map(str, task['pids'])) or '—') +
                    '  ·  私有内存 ' + size(task['private_mib']) + '  ·  有效进程读数 ' +
                    f"{task['sampled_pids']}/{task['process_count']}"))
            self.win_table.fill(rows)
            self.win_table.tkraise()
            self.show_win_selection()
            return
        self.model_table.tkraise()
        if kind == '27B 对话':
            items = [('项目选定模型', m.get('expected_model')), ('宿主报告模型', m.get('reported_model')),
                     ('实例计算后端', m.get('runner')), ('参数规模 / 量化', word(m.get('parameter_size')) + ' / ' + word(m.get('quantization'))),
                     ('模型格式', m.get('format')), ('Ollama 实例显存', byte_size(m.get('gpu_bytes'))),
                     ('宿主上下文上限', num(m.get('context_limit'), ' token')), ('实例上下文长度', num(m.get('instance_context'), ' token')),
                     ('当前 GPU 租约', num(active.get('llm'))), ('已接收生成请求', num(counts.get('accepted_llm'))),
                     ('板端本轮 LLM 调用', num(prep.get('llm_calls'), ' 次')), ('该轮 LLM 往返合计', num(prep.get('llm_rpc_ms'), ' ms'))]
            explanation = '板端组装角色、近期对话和输入。Ollama 用量化权重逐个预测下一个 token，宿主把完整的结构化回复交回板端。'
        elif kind == '语音合成':
            items = [('合成引擎', m.get('tts')), ('推理步数', num(m.get('steps'))),
                     ('子进程', yes(m.get('tts_alive'), '存活', '未运行')), ('同一预热实例', yes(m.get('tts_ready'), '就绪', '未就绪')),
                     ('语音请求活动', yes(m.get('tts_request'), '有活动请求', '待机')), ('当前 GPU 租约', num(active.get('tts'))),
                     ('预热 / 生成计数', num(m.get('tts_warmup')) + ' / ' + num(m.get('tts_generated'))),
                     ('其中冷启动 / 缓存命中', num(m.get('tts_cold_generated')) + ' / ' + num(m.get('tts_cache_hits'))),
                     ('上次保留显存峰值', byte_size(m.get('previous_reserved_peak_bytes'))),
                     ('上次保留显存增量峰值', byte_size(m.get('previous_extra_peak_bytes'))),
                     ('板端本轮 TTS 调用', num(prep.get('tts_calls'), ' 次')), ('该轮 TTS 往返合计', num(prep.get('tts_rpc_ms'), ' ms')),
                     ('该轮首音频入队', num(gui.get('latency', {}).get('first_audio_queued_ms'), ' ms'))]
            explanation = '板端分段提交台词。Windows 用已预热的 OmniVoice 生成语音，再传回板端播放并驱动口型。首音频入队计时止于软件队列。'
        elif kind == 'GPU 调度':
            card = next(iter(win.get('nvidia', {}).get('cards', [])), {})
            items = [('GPU', card.get('name')), ('整卡利用率', num(card.get('gpu_pct'), '%')),
                     ('整卡已用 / 总显存', size(card.get('memory_used_mib')) + ' / ' + size(card.get('memory_total_mib'))),
                     ('显卡温度', num(card.get('temperature_c'), ' °C')), ('调度模式', word(m.get('mode'))),
                     ('准入保护', yes(m.get('enforcing'), '生效', '关闭')),
                     ('LLM / TTS 有效租约', num(active.get('llm')) + ' / ' + num(active.get('tts'))),
                     ('GPU 排队 / 队列上限', num(win.get('gpu_queued')) + ' / ' + num(m.get('queue_limit'))),
                     ('上次准入结果', word(m.get('last_reason'))), ('上次准入等待', num(win.get('gpu_last_wait_ms'), ' ms')),
                     ('准入等待上限', num(m.get('max_wait_ms'), ' ms')),
                     ('LLM / TTS 累计准入', num(m.get('llm_admitted')) + ' / ' + num(m.get('tts_admitted')))]
            explanation = '两种模型共用一张 GPU。调度器结合驻留状态、显存余量和已有租约决定何时放行。整卡用量来自 NVIDIA，进程组占用来自 Windows 的 WDDM 计数器。'
        else:
            items = [('板端模型入口', '192.168.50.1:8797'), ('Ollama 本地端口', '127.0.0.1:11435'),
                     ('服务健康', '在线' if win.get('model_health_available') else '未取得'),
                     ('正在处理', yes(win.get('active'), '是', '否')),
                     ('请求排队 / 上限', num(win.get('pending')) + ' / ' + num(m.get('host_queue_limit'))),
                     ('已接收 LLM / TTS', num(counts.get('accepted_llm')) + ' / ' + num(counts.get('accepted_tts'))),
                     ('完成 / 失败 / 取消', ' / '.join(num(counts.get(k)) for k in ('completed', 'failed', 'cancelled'))),
                     ('超时请求', num(counts.get('deadline_exceeded'))), ('板端任务阶段', word(gui.get('processing', {}).get('task_state'))),
                     ('板端本轮 ASR', num(gui.get('latency', {}).get('asr_ms'), ' ms')),
                     ('板端本轮上下文准备', num(prep.get('context_ms'), ' ms')),
                     ('本份轮次计时', yes(gui.get('latency', {}).get('complete'), '已完成', '部分记录'))]
            explanation = '启动时先预热 OmniVoice，再装入固定的 27B 模型。运行时板端分别请求文本生成和语音合成，宿主记录请求计数。记忆、识别和播放由板端管理。'
        self.model_table.fill([{'id': name, 'name': name, 'value': word(value)} for name, value in items])
        self.model_explanation.configure(text=explanation)

    def draw_board(self, board):
        cam, gui = board.get('camera', {}), board.get('gui', {})
        pan, follow = gui.get('pan', {}), gui.get('follow', {})
        avatar, audio = gui.get('avatar', {}), gui.get('audio', {})
        if self.board_view.get() == '板端概览':
            rates = cam.get('rates', {})
            speaker, memory = gui.get('speaker', {}), gui.get('memory', {})
            listen, proc, lat = gui.get('listening', {}), gui.get('processing', {}), gui.get('latency', {})
            rows = [
                ('人脸与人体', yes(cam.get('identity', {}).get('ready'), '识别就绪', '识别未就绪'),
                 'YOLOX ' + num(rates.get('yolo'), '', 1) + '  ·  YuNet ' + num(rates.get('yunet'), '', 1) + ' 次/秒'),
                ('转轴跟随', yes(pan.get('automatic_following'), '已开启', '已关闭'), word(follow.get('reason')) +
                 '  ·  已接受 ' + num(follow.get('commands_accepted'), ' 条指令')),
                ('收音与识别', word(listen.get('state')), 'Paraformer  ·  麦克风' + yes(listen.get('microphone_open'), '已打开', '已关闭')),
                ('角色与播放', yes(avatar.get('visible'), '角色可见', '当前页隐藏'), yes(gui.get('playing'), '正在播放', '等待播放') +
                 '  ·  音频缓冲 ' + num(audio.get('queued_ms'), ' ms')),
                ('声纹与记忆', yes(speaker.get('ready'), '声纹就绪', '声纹未就绪'), '声纹完成 ' + num(speaker.get('complete')) +
                 '  ·  记忆维护完成 ' + num(memory.get('completed'))),
                ('最近轮次', word(proc.get('task_state')), '识别 ' + num(lat.get('asr_ms'), ' ms') +
                 '  ·  首音频入队 ' + num(lat.get('first_audio_queued_ms'), ' ms')),
            ]
            self.board_summary.fill([dict(id=name, name=name, state=state, detail=detail) for name, state, detail in rows])
            self.board_summary.tkraise()
            if board.get('online'):
                self.board_note.configure(text='业务接口' + yes(gui.get('available'), '在线', '未取得') + '  ·  相机接口' +
                    yes(cam.get('available'), '在线', '未取得') + '  ·  界面故障 ' + num(gui.get('faults', {}).get('count')) +
                    '  ·  功能与进程组可查看各项资源归属')
            else:
                self.board_note.configure(text=board.get('error') or '等待板端采样')
            return
        rows = []
        for row in board_tasks(board):
            detail = row['detail']
            for code in ('WAITING_SPEECH', 'MONITORING', 'CONFIRMING', 'WAITING_FOR_FACE', 'FOLLOWING', 'IDLE_READY'):
                detail = detail.replace(code, WORDS[code])
            pids = ', '.join(map(str, row['pids'])) or '—'
            rows.append(dict(id=row['id'], name=row['name'], state=row['state'], detail=detail,
                cpu='共享' if row['shared'] else num(row['cpu_pct'], '%', 1),
                rss='共享' if row['shared'] else size(row['rss_mib']),
                _detail=row['name'] + '  ·  ' + detail + '  ·  所属进程组 ' + row['owner'] + '  ·  PID ' + pids,
                _sort={'cpu': row['cpu_pct'], 'rss': row['rss_mib']}))
        self.board_table.fill(rows)
        self.board_table.tkraise()
        self.show_board_selection()

    def draw_inventory(self, win, board):
        service_view = self.kind.get() == '服务'
        table, other = (self.service_table, self.process_table) if service_view else (self.process_table, self.service_table)
        other.pack_forget()
        if table.winfo_manager() != 'pack':
            table.pack(fill='both', expand=True)
        rows = []
        search = self.search.get().strip().casefold()
        totals = []
        for device, source in [('Windows', win), ('KV260', board)]:
            if self.device.get() not in ('两端', device):
                continue
            procs = source.get('processes', [])
            items = source.get('services' if service_view else 'processes')
            totals.append(device + ' ' + (str(len(items)) if items is not None else '待采样'))
            if items is None:
                continue
            role_names = PC_ROLES if device == 'Windows' else ROLE_NAMES
            project_pids = {proc['pid'] for proc in procs if proc['role']}
            unit_pids = {}
            if service_view and device == 'KV260':
                for proc in procs:
                    unit_pids.setdefault(proc['unit'], []).append(proc['pid'])
            for item in items:
                if service_view:
                    unit = item['unit']
                    pids = unit_pids.get(unit, []) if device == 'KV260' else ([item['pid']] if item.get('pid') else [])
                    belongs = bool(project_pids.intersection(pids)) or unit.startswith('aura-')
                    row = dict(id=device + '/' + unit, device=device, name=unit, info=item.get('name') or word(item.get('load')),
                               state=word(item.get('state') or item.get('active')), mode=word(item.get('mode') or item.get('sub')),
                               pid=', '.join(map(str, pids)) or '—')
                else:
                    belongs = bool(item['role'])
                    row = dict(id=f"{device}/{item['pid']}/{item.get('birth')}", device=device, name=item['name'],
                        pid=item['pid'], ppid=item['ppid'], role=role_names.get(item['role']) or item.get('unit') or '系统 / 其他',
                        threads=item['threads'], cpu=num(item.get('cpu_pct'), '%', 1), rss=size(item.get('rss_mib')),
                        gpu=num(item.get('gpu_pct'), '%', 1), vram=size(item.get('vram_mib')),
                        _sort={'cpu': item.get('cpu_pct'), 'rss': item.get('rss_mib'), 'gpu': item.get('gpu_pct'), 'vram': item.get('vram_mib')})
                if self.scope.get() != '全部' and not belongs:
                    continue
                if search and not any(search in str(row.get(key, '')).casefold() for key in table.columns):
                    continue
                rows.append(row)
        table.fill(rows)
        scope_note = 'Windows 注册服务  ·  KV260 已加载服务' if service_view else '点击列名排序'
        if not service_view and board.get('skipped_pids') and self.device.get() != 'Windows':
            scope_note += '  ·  板端采样时退出或不可读 ' + num(board['skipped_pids'], ' 项')
        self.inventory_note.configure(text='本次枚举   ' + '   /   '.join(totals) + f'       当前显示 {len(rows)} 行   ·   ' + scope_note)

    def collect(self, key, factory, interval):
        sampler = None
        try:
            sampler = factory()
            while not self.stop.is_set():
                began = time.monotonic()
                try:
                    value = sampler.sample()
                except Exception as error:
                    value = {'online': False, 'error': type(error).__name__}
                self.inbox.put((key, value))
                self.stop.wait(max(.2, interval - (time.monotonic() - began)))
        except Exception as error:
            self.inbox.put((key, {'online': False, 'error': type(error).__name__}))
        finally:
            if sampler:
                sampler.close()

    def tick(self):
        changed = False
        while True:
            try:
                key, value = self.inbox.get_nowait()
            except queue.Empty:
                break
            self.latest[key] = value
            self.pc_samples += int(key == 'win' and 'tasks' in value)
            changed = True
        if changed and not self.paused:
            self.shown = self.latest.copy()
            self.render()
        board = self.latest['board']
        if self.args.screenshot and self.pc_samples >= 3 and board and (not board.get('online') or board.get('system_cpu_pct') is not None):
            path, self.args.screenshot = self.args.screenshot, None
            self.root.after(150, lambda: self.capture_window(self.root, path))
        if not self.stop.is_set():
            self.root.after(140, self.tick)

    def pause(self):
        self.paused = not self.paused
        self.pause_button.configure(text='继续显示' if self.paused else '暂停显示')
        if not self.paused:
            self.shown = self.latest.copy()
        self.render()

    def fullscreen(self, event=None):
        self.set_fullscreen(not self.full)

    def set_fullscreen(self, value):
        self.full = value
        self.root.attributes('-fullscreen', value)

    def close(self):
        if self.stop.is_set():
            return
        self.stop.set()
        self.root.withdraw()
        def finish():
            if any(worker.is_alive() for worker in self.threads):
                self.root.after(100, finish)
            else:
                self.root.destroy()
        finish()

    def help(self):
        messagebox.showinfo('采样与指标', '电脑每 2 秒读取进程、WDDM、NVIDIA、模型健康和 Ollama 驻留状态。进程归属和 Windows 服务列表每 10 秒更新。\\n\\n'
            '板端每 5 秒经现有 SSH 连接读取 /proc、systemd 和本机业务状态。关闭窗口时采集会话退出。\\n\\n'
            '两端 CPU 都以整机所有逻辑核的容量为 100%。进程组内存是工作集或 RSS 之和，共享页可能重复计入。'
            'Windows 任务 GPU 取最忙 WDDM 引擎，整卡 GPU 来自 NVIDIA。Ollama 模型显存、WDDM 专用显存和 TTS 分配器峰值各有独立口径。\\n\\n'
            '共享功能可查看所属进程。— 表示量值暂缺。瞬时任务可能发生于两次采样之间。F11 切换全屏，Esc 退出全屏。'.replace('\\n', '\n'), parent=self.root)
