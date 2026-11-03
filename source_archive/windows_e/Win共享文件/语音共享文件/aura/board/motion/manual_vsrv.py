"""Guarded board adapter for finite calibration, without a claimed physical zero."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
import urllib.request
import urllib.error

from board.motion import vsrv_driver as driver_module
from board.motion.vsrv_driver import VSRVDriver, BIND, REFERENCE, ARM, COMMIT


class ManualCommandError(RuntimeError):
    def __init__(self, message, detail):
        super().__init__(message)
        self.detail = detail


class ManualVSRV:
    def __init__(self, config):
        self.config = config
        self.io = self.driver = None
        self.seq = 0
        self.last_ack_time = None
        self.timing = {}

    def verify_platform(self):
        if os.uname().machine != 'aarch64' or os.geteuid() != 0:
            raise RuntimeError('转轴接口仅在KV260上可用')
        assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == self.config['boot_id'], 'Boot mismatch'
        assert hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest() == self.config['fdt_sha256'], 'FDT mismatch'
        assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode() == 'aura-visual-servo-b4096-v1.bit.bin', 'Joint firmware required'
        assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip() == 'operating'
        assert Path('/etc/vart.conf').read_text() == 'firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-v1/aura-visual-servo-b4096-v1.xclbin\n'

    def __enter__(self):
        self.verify_platform()
        root = Path(self.config['driver_root']).resolve(strict=True)
        assert hashlib.sha256((root/'common.py').read_bytes()).hexdigest() == 'f529550d981a6114b669353db08c05174a6e45221c6385456d40896c18b0cc4a'
        assert hashlib.sha256(Path(driver_module.__file__).read_bytes()).digest() == hashlib.sha256((root/'vsrv_driver.py').read_bytes()).digest(), 'Driver source mismatch'
        spec = importlib.util.spec_from_file_location('_aura_manual_pan_guard', root/'common.py')
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        guard.BOOT = self.config['boot_id']
        guard.guard()
        guard.check_runtime()
        assert guard.active() == [guard.APP] and guard.firmware() == guard.APP+'.bit.bin'
        try:
            spec = importlib.util.spec_from_file_location('_aura_manual_pan_transport', root/'vsrv_transport.py')
            transport = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(transport)
            self.io = transport.NativeRegisters(root/'libvsrv.so', guard.MANIFEST['payload_files']['libvsrv.so'],
                                                guard.BOOT, guard.runtime_hashes())
            self.driver = VSRVDriver(self.io, 0x14da0e60, guard.BOOT)
            self.session = int.from_bytes(os.urandom(4), 'big') or 1
            return self
        except BaseException:
            if self.io:
                self.io.close()
            raise

    def __exit__(self, *args):
        try:
            if self.driver:
                self.driver.stop()
        finally:
            if self.io:
                self.io.close()

    def before_move(self):
        self.verify_platform()
        # A manual step must not disturb an enrollment already sampling faces.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open('http://127.0.0.1:8790/v1/ui/status', timeout=.25) as response:
                value = json.load(response)
        except (urllib.error.URLError, OSError, ValueError):
            raise ValueError('相机状态暂不可用，请稍后再试') from None
        identity = value.get('modules', {}).get('identity', {}).get('state')
        if identity in ('ENROLLING', 'SAMPLING'):
            raise ValueError('正在登记身份，请稍后再调节转轴')

    def status(self):
        return self.driver.status()

    def stop(self):
        return self.driver.stop()

    def begin(self, before):
        current = self.status()
        assert current == before and current['flags'] == 0 and current['lease_left_ms'] == 0
        assert 1400 <= current['width_us'] <= 1600 and current['epoch'] < 0xffffffff
        self.epoch, self.seq = current['epoch'] + 1, 0
        self.last_ack_time = None
        self.timing = dict(max_ack_gap_ms=0, max_commit_ms=0)
        self.io.write(0x10, self.session)
        self.io.write(0x14, self.epoch)
        self.io.write(0x24, BIND)
        state = self.status()
        assert state['flags'] == 8 and state['session'] == self.session and state['epoch'] == self.epoch and state['ack_seq'] == 0
        self.io.write(0x3c, current['width_us'])
        self.io.write(0x24, REFERENCE)
        state = self.status()
        assert state['flags'] == 12 and state['reference_us'] == current['width_us'] and state['width_us'] == current['width_us']
        self.io.write(0x24, ARM)
        assert self.status()['flags'] == 14

    def commit(self, target):
        assert type(target) is int and 1400 <= target <= 1600
        started = time.monotonic()
        before = self.status()
        gap = (started-self.last_ack_time)*1000 if self.last_ack_time is not None else 0
        if (before['flags'] & 14 != 14 or before['session'] != self.session
                or before['epoch'] != self.epoch or before['ack_seq'] != self.seq):
            raise ManualCommandError('运动许可已失效，已停止；请重新连接后再手动点动',
                                     dict(before=before, gap_since_ack_ms=round(gap, 3), attempted_seq=self.seq+1))
        self.seq += 1
        self.io.write(0x18, self.seq)
        self.io.write(0x1c, target)
        self.io.write(0x20, 100)
        self.io.write(0x24, COMMIT)
        state = self.status()
        finished = time.monotonic()
        self.timing['max_ack_gap_ms'] = max(self.timing['max_ack_gap_ms'], round(gap, 3))
        self.timing['max_commit_ms'] = max(self.timing['max_commit_ms'], round((finished-started)*1000, 3))
        if not (state['active'] and state['reason'] == 0 and state['ack_seq'] == self.seq
                and state['target_us'] == target and state['session'] == self.session and state['epoch'] == self.epoch):
            raise ManualCommandError('指令回读异常，已停止；请重新连接后再手动点动',
                                     dict(before=before, after=state, attempted_seq=self.seq,
                                          commit_ms=round((finished-started)*1000, 3), gap_since_ack_ms=round(gap, 3)))
        self.last_ack_time = finished
        return state
