"""Attribution, privacy and telemetry loss cases for the dual-device observer."""
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from model_runtime_dashboard import descendants, model_detail
from runtime_board_monitor import BoardSampler, board_tasks, prepare_sample
from runtime_board_probe import gui_status, proc_stat, service_name


def sample(boot, total, idle, ticks, birth=23):
    return {'schema': 1, 'boot_id': boot, 'total_ticks': total, 'idle_ticks': idle, 'monotonic': total / 100,
            'processes': [{'pid': 17, 'birth': birth, 'ticks': ticks, 'role': 'gui', 'rss_mib': 14.5}],
            'camera': {'available': False}, 'gui': {'available': True, 'memory': {'running': True}}}


class DualMonitor(unittest.TestCase):
    def test_tts_generated_excludes_warmup_and_cache_but_includes_cold_generation(self):
        counts = {'warmup': 1, 'generated': 8, 'cold_generated': 1, 'cache_hit': 2}
        response = {'ok': True, 'data': {'ok': True, 'role': 'model_inference_only', 'protocol_version': 1,
                    'backend': {'gpu_coordination': {'tts_counts': counts}}}}
        value = model_detail(response, None, 'model')
        self.assertEqual((value['tts_generated'], value['tts_warmup'], value['tts_cache_hits']), (9, 1, 2))
        self.assertIsNone(model_detail(None, None, 'model')['tts_generated'])

    def test_failed_ssh_discards_the_previous_generation(self):
        client = BoardSampler()
        client.previous = sample('A', 100, 50, 4)
        with patch.object(client, 'connect', side_effect=OSError('unavailable')):
            result = client.sample()
        self.assertFalse(result['online'])
        self.assertIsNone(client.previous)
        self.assertNotIn('processes', result)

    @unittest.skipUnless(os.name == 'nt', 'native Windows dashboard')
    def test_both_devices_stay_in_view_during_drilldown_filtering_and_disconnect(self):
        import tkinter as tk
        from runtime_dashboard_ui import Dashboard
        root = tk.Tk()
        self.addCleanup(root.destroy)
        root.attributes('-alpha', 0)
        with patch.object(Dashboard, 'collect', return_value=None):
            app = Dashboard(root, SimpleNamespace(view='overview', close_after=0, screenshot=None),
                            None, None, 'AURA layout check')
        base = dict(ppid=0, threads=2, birth=15, rss_mib=4)
        win = dict(tasks=[], processes=[dict(base, pid=4, name='runner.exe', role='llm')],
                   services=[dict(unit='test', name='Test', state='Running', mode='Auto', pid=4)])
        board = dict(online=True, gui={}, camera={}, processes=[dict(base, pid=5, name='python3', role='camera',
                     unit='aura-camera-ui.service')], services=[dict(unit='aura-camera-ui.service', load='loaded',
                     active='active', sub='running')])
        app.shown = {'win': win, 'board': board}
        app.render()
        root.deiconify()
        root.update()
        self.assertLessEqual(app.win_trend.winfo_rootx() + app.win_trend.winfo_width(), app.board_trend.winfo_rootx())
        self.assertEqual(app.win_trend.winfo_rooty(), app.board_trend.winfo_rooty())
        self.assertTrue(app.win_trend.winfo_ismapped() and app.board_trend.winfo_ismapped())
        self.assertEqual(len(app.process_table.rows), 2)
        for view in ('27B 对话', '语音合成', 'GPU 调度', '请求宿主', '项目进程组'):
            app.model_view.set(view)
            app.board_view.set('功能与进程组')
            app.render()
            self.assertIn('camera', app.board_table.rows)
            self.assertTrue(app.win_trend.winfo_ismapped() and app.board_trend.winfo_ismapped())
        app.kind.set('服务')
        app.search.set('aura-camera')
        self.assertEqual(set(app.service_table.rows), {'KV260/aura-camera-ui.service'})
        app.search.set('')
        self.assertEqual(len(app.service_table.rows), 2)
        app.shown['board'] = {'online': False, 'error': '断开'}
        app.render()
        self.assertEqual(set(app.service_table.rows), {'Windows/test'})
        self.assertFalse(app.board_table.rows)
        self.assertIn('KV260 未连接', app.live.cget('text'))

    def test_other_resident_model_cannot_impersonate_the_project_model(self):
        response = {'ok': True, 'data': {'models': [{'name': 'different', 'size_vram': 15000}]}}
        self.assertIs(model_detail(None, response, 'project')['resident'], False)
        self.assertIsNone(model_detail(None, response, 'project')['gpu_bytes'])
        self.assertIsNone(model_detail(None, None, 'project')['resident'])

    def test_reused_windows_parent_pid_cannot_claim_older_child(self):
        procs = {1: {'ppid': 0, 'birth': 50}, 2: {'ppid': 1, 'birth': 30}, 3: {'ppid': 1, 'birth': 60}}
        self.assertEqual(descendants({1}, procs), {1, 3})

    def test_board_cpu_normalizes_for_whole_machine_and_rejects_reused_identity(self):
        first = prepare_sample(sample('A', 1000, 500, 3), None)
        current = prepare_sample(sample('A', 1400, 800, 103), first)
        self.assertEqual(current['system_cpu_pct'], 25)
        self.assertEqual(current['processes'][0]['cpu_pct'], 25)
        changed_owner = prepare_sample(sample('A', 1800, 1000, 903, birth=42), current)
        self.assertIsNone(changed_owner['processes'][0]['cpu_pct'])
        new_boot = prepare_sample(sample('B', 2100, 1020, 1200), current)
        self.assertIsNone(new_boot['system_cpu_pct'])
        self.assertIsNone(new_boot['processes'][0]['cpu_pct'])

    def test_shared_workers_do_not_duplicate_resources(self):
        board = prepare_sample(sample('A', 1200, 710, 33), prepare_sample(sample('A', 1000, 600, 3), None))
        tasks = {row['id']: row for row in board_tasks(board)}
        self.assertEqual(tasks['gui']['cpu_pct'], 15)
        self.assertEqual(tasks['memory']['pids'], [17])
        self.assertIsNone(tasks['memory']['cpu_pct'])
        self.assertIsNone(tasks['memory']['rss_mib'])

    def test_private_values_never_leave_the_board_projection(self):
        doc = {'ui_page': 'main', 'reply': 'PRIVATE-REPLY', 'turns': ['PRIVATE-HISTORY'],
               'board_business': {'dialogue': {'last_playback_ack': {'request_id': 'PRIVATE-ID', 'committed': True},
                   'latency': {'prepare': {'llm_rpc_ms': 75, 'messages': 'PRIVATE-PROMPT'}}}}}
        out = gui_status(doc)
        self.assertNotIn('PRIVATE-', json.dumps(out))
        self.assertTrue(out['ack']['committed'])
        self.assertEqual(out['prepare'], {'llm_rpc_ms': 75})

    def test_process_name_with_parenthesis_and_cgroup_versions(self):
        line = '12 (odd ) worker) S 1 2 3 4 5 6 7 8 9 10 13 14 15 16 17 18 19 20 21 22 23'
        self.assertEqual(proc_stat(line)['name'], 'odd ) worker')
        self.assertEqual(proc_stat(line)['ticks'], 27)
        self.assertEqual(service_name('0::/system.slice/aura-avatar-ui.service\n'), 'aura-avatar-ui.service')
        self.assertEqual(service_name('4:cpu:/system.slice/aura-camera-ui.service\n2:net:/\n'), 'aura-camera-ui.service')


if __name__ == '__main__':
    unittest.main()
