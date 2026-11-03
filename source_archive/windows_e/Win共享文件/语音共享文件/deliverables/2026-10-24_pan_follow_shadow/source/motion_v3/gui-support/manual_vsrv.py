"""Guarded board adapter for finite calibration, without a claimed physical zero."""
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request
import urllib.error

from board.motion import vsrv_driver as driver_module
from board.motion.vsrv_driver import VSRVDriver, BIND, REFERENCE, ARM, COMMIT, ABI, BUILD_ID
from board.motion.vsrv_transport import NativeRegisters
from board.motion.manual_release import observed_bounds

APP = 'aura-visual-servo-b4096-v2'


def load_release(config):
    """Require a separately qualified, byte-pinned release before any MMIO.

    The delivered template stays disabled. Offline test success must never
    turn into a motion permit simply by copying this candidate to the board.
    """
    if config.get('enabled') is not True:
        raise RuntimeError('转轴修复候选尚未放行，保持锁定')
    manifest_path = Path(config['release_manifest']).resolve(strict=True)
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != config['release_manifest_sha256']:
        raise RuntimeError('Release manifest hash mismatch; no MMIO')
    release = json.loads(manifest_path.read_text())
    if (release.get('schema_version') != 1
            or release.get('abi') != ABI or release.get('build_id') != BUILD_ID
            or release.get('app') != APP):
        raise RuntimeError('VSRV2 release is not qualified; no MMIO')
    root = manifest_path.parent
    if release.get('status')=='OBSERVED_MANUAL_VSRV2':
        observed_bounds(release,config,root)
    elif (release.get('status')!='QUALIFIED_VSRV2' or any(release.get(key) is not True for key in
            ('external_waveform_verified','physical_servo_response_verified','dpu_coexistence_verified'))):
        raise RuntimeError('VSRV2 release is not qualified; no MMIO')
    required = {'libvsrv.so', 'vsrv_transport.py', 'vsrv_driver.py'}
    if set(release['payload_files']) != required:
        raise RuntimeError('Exact VSRV2 payload required; no MMIO')
    for name, digest in release['payload_files'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Release payload mismatch; no MMIO')
    if hashlib.sha256(Path(driver_module.__file__).read_bytes()).hexdigest() != release['payload_files']['vsrv_driver.py']:
        raise RuntimeError('Active driver source mismatch; no MMIO')
    import board.motion.vsrv_transport as transport_module
    if hashlib.sha256(Path(transport_module.__file__).read_bytes()).hexdigest() != release['payload_files']['vsrv_transport.py']:
        raise RuntimeError('Active transport source mismatch; no MMIO')
    required_runtime = {f'/lib/firmware/xilinx/{APP}/{APP}'+ext for ext in ('.bit.bin', '.dtbo', '.xclbin')}
    if not required_runtime.issubset(release['runtime_files']):
        raise RuntimeError('Joint firmware hashes missing; no MMIO')
    for name, digest in release['runtime_files'].items():
        if not Path(name).is_absolute() or hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Installed runtime mismatch; no MMIO')
    return root, release


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
        self.release_root, self.release = load_release(self.config)
        checks = [
            Path('/proc/sys/kernel/random/boot_id').read_text().strip() == self.config['boot_id'],
            Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100',
            hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest() == self.config['fdt_sha256'],
            Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode() == APP+'.bit.bin',
            Path('/sys/class/fpga_manager/fpga0/state').read_text().strip() == 'operating',
            Path('/etc/vart.conf').read_text() == f'firmware: /lib/firmware/xilinx/{APP}/{APP}.xclbin\n',
        ]
        if not all(checks):
            raise RuntimeError('Exact board/boot/firmware/VART context required; no MMIO')

    def __enter__(self):
        self.verify_platform()
        root, release = self.release_root, self.release
        try:
            self.io = NativeRegisters(root/'libvsrv.so', release['payload_files']['libvsrv.so'],
                                      self.config['boot_id'], release['runtime_files'])
            self.driver = VSRVDriver(self.io, BUILD_ID, self.config['boot_id'])
            state=self.driver.status()
            minimum=self.config.get('manual_minimum_us',1400)
            maximum=self.config.get('manual_maximum_us',1600)
            self.stopped_face_resume = False
            if not minimum<=state['width_us']<=maximum:
                from board.motion.follow_readback import verified_stopped_face_command
                self.stopped_face_resume = verified_stopped_face_command(self.config,state)
            if state['flags']!=0 or state['lease_left_ms']!=0 or not (minimum<=state['width_us']<=maximum or self.stopped_face_resume):
                raise RuntimeError('转轴读回不在本次已观察范围，请重新确认位置')
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

    def finish(self):
        return self.driver.finish()

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
        if not self.config.get('manual_minimum_us',1400)<=target<=self.config.get('manual_maximum_us',1600):
            raise ValueError('超出本次已观察的手动范围')
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
