"""Bounded, read-only MCP01 kernel incident evidence; no recovery actions.

Only fixed /proc and /sys metadata, two local GET endpoints, and readonly
journalctl/systemctl commands are used. No audio payload, face box, identity,
conversation text, device stream, private argv, or MMIO is collected.
"""
import argparse
import json
import os
import re
import selectors
import subprocess
import time
import urllib.request
from pathlib import Path

POLL_SECONDS = 10.
INCIDENT_GAP_SECONDS = 60.
MAX_INCIDENTS = 3
MAX_DURATION_SECONDS = 7200.
MAX_JOURNAL_LINES = 120
MAX_JOURNAL_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 1024 * 1024
MAX_INCIDENT_BYTES = 128 * 1024
MAX_PROGRESS_BYTES = 512 * 1024
WARNING = "xhci-hcd xhci-hcd.1.auto: WARN: HC couldn't access mem fast enough for slot 4 ep 3"
PCM = '/proc/asound/card1/pcm0p/sub0'
USB = '/sys/bus/usb/devices/1-1.2'
SLOT = '/sys/kernel/debug/usb/xhci/xhci-hcd.1.auto/devices/04'


class CaptureError(RuntimeError):
    pass


def boot_key(value):
    if not isinstance(value, str):
        raise CaptureError('Invalid boot identity type')
    value = value.strip().lower().replace('-', '')
    if not re.fullmatch('[0-9a-f]{32}', value):
        raise CaptureError('Invalid boot identity')
    return value


def numeric(value, name):
    if type(value) is not int or value < 0:
        raise CaptureError('Invalid numeric field: ' + name)
    return value


def command(args, limit, timeout=2.):
    """Drain a small owned readonly command with both time and byte limits."""
    allowed = args == ['systemctl', 'show', 'aura-avatar-ui.service', '-p', 'MainPID', '--value']
    if len(args) >= 4 and args[0] == 'journalctl':
        allowed = args == ['journalctl', '-k', '-b', boot_key(args[3]), '--no-pager', '-n', '120', '-o', 'json',
                           '--output-fields=_BOOT_ID,_TRANSPORT,__MONOTONIC_TIMESTAMP,MESSAGE']
    if not allowed:
        raise CaptureError('Only readonly metadata commands are permitted')
    child = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             close_fds=True)
    data = bytearray()
    end = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            while selector.get_map():
                left = end - time.monotonic()
                if left <= 0:
                    raise CaptureError('Metadata command timed out: ' + args[0])
                for key, _ in selector.select(left):
                    chunk = os.read(key.fileobj.fileno(), min(8192, limit + 1 - len(data)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    data.extend(chunk)
                    if len(data) > limit:
                        raise CaptureError('Metadata command exceeded byte limit: ' + args[0])
            code = child.wait(timeout=max(.01, end - time.monotonic()))
        if code:
            raise CaptureError('Metadata command failed: ' + args[0])
        return bytes(data).decode('utf-8', 'strict')
    finally:
        if child.poll() is None:
            child.kill()  # This is only our readonly metadata child.
            child.wait(timeout=1.)
        child.stdout.close()


class JournalGate:
    def __init__(self, boot, started_us):
        self.boot = boot_key(boot)
        self.last_us = self.started_us = started_us

    def consume(self, raw, now_us):
        if len(raw.encode()) > MAX_JOURNAL_BYTES:
            raise CaptureError('Journal payload exceeds byte limit')
        lines = raw.splitlines()
        if len(lines) > MAX_JOURNAL_LINES:
            raise CaptureError('Journal payload exceeds line limit')
        stamps = set()
        filtered = dict(other_boot=0, other_message=0, historical_or_duplicate=0, future=0)
        for line in lines:
            try:
                row = json.loads(line)
                stamp_text = row['__MONOTONIC_TIMESTAMP']
                if not isinstance(stamp_text, str) or not stamp_text.isdecimal():
                    raise ValueError('timestamp must be decimal microseconds')
                stamp = int(stamp_text)
                row_boot = boot_key(row['_BOOT_ID'])
            except (KeyError, TypeError, ValueError) as exc:
                raise CaptureError('Invalid journal metadata') from exc
            if row_boot != self.boot:
                filtered['other_boot'] += 1
            elif row.get('_TRANSPORT') != 'kernel' or row.get('MESSAGE') != WARNING:
                filtered['other_message'] += 1
            elif stamp > now_us:
                filtered['future'] += 1
            elif stamp <= self.last_us or stamp in stamps:
                filtered['historical_or_duplicate'] += 1
            else:
                stamps.add(stamp)
        fresh = sorted(stamps)
        if fresh:
            self.last_us = fresh[-1]
        return dict(sampled_lines=len(lines), sample_capped=len(lines) == MAX_JOURNAL_LINES,
                    new_warning_timestamps_us=fresh, filtered=filtered,
                    scope='last120 kernel entries only; deduplicated timestamps, not a complete error rate')


def pcm_fields(raw):
    values = {}
    for line in raw.splitlines():
        if ':' not in line:
            continue
        key, value = (part.strip() for part in line.split(':', 1))
        if key in ('state', 'owner_pid', 'delay', 'avail', 'avail_max', 'hw_ptr', 'appl_ptr'):
            if key == 'state':
                values[key] = value[:24]
            elif re.fullmatch('-?[0-9]+', value):
                values[key] = int(value)
            else:
                raise CaptureError('Invalid PCM numeric status')
    if values.get('state') != 'RUNNING':
        raise CaptureError('PCM_NOT_RUNNING')
    for name in ('owner_pid', 'hw_ptr', 'appl_ptr'):
        numeric(values.get(name), name)
    return values


class Platform:
    def __init__(self, camera_pid, gui_pid, root=Path('/')):
        self.camera_pid, self.gui_pid, self.root = camera_pid, gui_pid, root
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.boot = boot_key(self.read('/proc/sys/kernel/random/boot_id', 128))
        self.births = None
        self.audio_owner = None

    def read(self, name, limit=8192):
        with (self.root / name.lstrip('/')).open('rb') as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise CaptureError('Metadata file exceeds limit: ' + name)
        return raw.decode('utf-8', 'strict')

    def get(self, port, path):
        with self.opener.open('http://127.0.0.1:%d%s' % (port, path), timeout=2) as response:
            raw = response.read(512 * 1024 + 1)
        if len(raw) > 512 * 1024:
            raise CaptureError('HTTP metadata exceeds limit')
        return json.loads(raw)

    def check(self):
        if boot_key(self.read('/proc/sys/kernel/random/boot_id', 128)) != self.boot:
            raise CaptureError('BOARD_BOOT_CHANGED')
        health = self.get(8790, '/health')
        ui = self.get(8783, '/api/state')
        gui = command(['systemctl', 'show', 'aura-avatar-ui.service', '-p', 'MainPID', '--value'], 128)
        if health['pid'] != self.camera_pid or int(gui.strip()) != self.gui_pid:
            raise CaptureError('RUNTIME_OWNER_CHANGED')
        births = []
        for pid in (self.camera_pid, self.gui_pid):
            fields = self.read('/proc/%d/stat' % pid, 4096).rsplit(')', 1)[1].split()
            births.append(int(fields[19]))
        if self.births is not None and births != self.births:
            raise CaptureError('RUNTIME_PID_REUSED')
        self.births = births
        if self.read('/proc/asound/card1/usbid', 128).strip().lower() != '17ef:a03b':
            raise CaptureError('ALSA_CARD_IDENTITY_CHANGED')
        if (self.read(USB + '/idVendor', 128).strip().lower() != '17ef'
                or self.read(USB + '/idProduct', 128).strip().lower() != 'a03b'
                or self.read(SLOT + '/name', 128).strip() != '1-1.2'):
            raise CaptureError('USB_SLOT_IDENTITY_CHANGED')
        pcm = pcm_fields(self.read(PCM + '/status'))
        if self.audio_owner is not None and pcm['owner_pid'] != self.audio_owner:
            raise CaptureError('AUDIO_OWNER_CHANGED')
        self.audio_owner = pcm['owner_pid']
        sch, manual = health['dpu_schedule'], ui['manual_pan']
        readback = manual['readback']
        return dict(camera_pid=self.camera_pid, gui_pid=self.gui_pid,
                    process_birth_ticks=births, audio_owner_pid=self.audio_owner,
                    primary_overruns=numeric(sch['primary_period_overruns'], 'primary_overruns'),
                    owner_fenced=bool(sch['owner_fenced']), automatic_following=bool(manual['automatic_following']),
                    flags=numeric(readback['flags'], 'flags'), width_us=numeric(readback['width_us'], 'width_us'),
                    lease_ms=numeric(readback['lease_left_ms'], 'lease_ms'),
                    phase=str(ui.get('phase', ''))[:32], audio_state=str(ui.get('audio_output_state', ''))[:32])

    def journal(self):
        return command(['journalctl', '-k', '-b', self.boot, '--no-pager', '-n', '120', '-o', 'json',
                        '--output-fields=_BOOT_ID,_TRANSPORT,__MONOTONIC_TIMESTAMP,MESSAGE'], MAX_JOURNAL_BYTES)

    def counters(self):
        interrupts = []
        for line in self.read('/proc/interrupts', 128 * 1024).splitlines():
            if ':' in line and re.search('xhci|dwc|usb', line, re.I):
                left, right = line.split(':', 1)
                values = right.split()
                counts = []
                while values and values[0].isdigit():
                    counts.append(int(values.pop(0)))
                interrupts.append(dict(irq=left.strip(), per_cpu_counts=counts,
                                       description=' '.join(values)[:256]))
        cpu = {}
        for line in self.read('/proc/stat', 128 * 1024).splitlines():
            values = line.split()
            if values and re.fullmatch('cpu[0-9]*|ctxt|processes|procs_running|procs_blocked|intr', values[0]):
                cpu[values[0]] = [int(v) for v in (values[1:2] if values[0] == 'intr' else values[1:])][:10]
        load = self.read('/proc/loadavg', 512).split()
        return dict(interrupts=interrupts[:32], irq_rows_capped=len(interrupts) > 32,
                    cpu={k:cpu[k] for k in list(cpu)[:24]}, loadavg=[float(v) for v in load[:3]])

    def context(self):
        return dict(usb={name:self.read(USB + '/' + name, 1024).strip() for name in
                         ('idVendor', 'idProduct', 'speed', 'power/runtime_status', 'power/control')},
                    slot={name:self.read(SLOT + '/' + name, 16384).strip() for name in
                          ('name', 'slot-context', 'ep-context')},
                    hw_params=self.read(PCM + '/hw_params', 4096), sw_params=self.read(PCM + '/sw_params', 4096))

    def capture(self, clock, sleep, end):
        self.check()
        if end - clock() < 3.:
            raise CaptureError('INSUFFICIENT_TIME_FOR_INCIDENT')
        context = self.context()
        before = self.counters()
        start = clock()
        rows = []
        while True:
            row = pcm_fields(self.read(PCM + '/status'))
            if row['owner_pid'] != self.audio_owner:
                raise CaptureError('AUDIO_OWNER_CHANGED_DURING_INCIDENT')
            row['elapsed_s'] = round(clock() - start, 6)
            rows.append(row)
            remaining = 3. - (clock() - start)
            if remaining <= 0:
                break
            sleep(min(.25, remaining))
        after = self.counters()
        owner = self.check()
        first, last = rows[0], rows[-1]
        return dict(context=context, before=before, after=after, owner_after=owner,
                    pcm_samples=rows, span_s=last['elapsed_s'] - first['elapsed_s'],
                    raw_pointer_delta={k:last[k] - first[k] for k in ('hw_ptr', 'appl_ptr')},
                    internal_appsrc_queue_observed=False, USB_root_cause_proven=False)


class BoundedOutput:
    def __init__(self, directory):
        directory = Path(directory)
        parent = directory.parent.resolve(strict=True)
        self.path = parent / directory.name
        self.path.mkdir(mode=0o700)  # Existing paths/symlinks are never reused.
        self.fd = os.open(str(self.path), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.total = self.progress_bytes = 0
        self.progress_fd = self._new('progress.jsonl')

    def _new(self, name):
        if not re.fullmatch('[a-z0-9_.-]+', name):
            raise CaptureError('Invalid evidence filename')
        return os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)

    def _write(self, fd, raw):
        if self.total + len(raw) > MAX_TOTAL_BYTES:
            raise CaptureError('Evidence total byte limit')
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise CaptureError('Evidence write failed')
            self.total += written
            view = view[written:]

    def write(self, name, value, limit=MAX_INCIDENT_BYTES):
        raw = (json.dumps(value, separators=(',', ':'), ensure_ascii=False) + '\n').encode()
        if len(raw) > limit or self.total + len(raw) > MAX_TOTAL_BYTES - (0 if name == 'result.json' else 8192):
            raise CaptureError('Evidence file byte limit')
        fd = self._new(name)
        try:
            self._write(fd, raw)
        finally:
            os.close(fd)

    def progress(self, value):
        raw = (json.dumps(value, separators=(',', ':')) + '\n').encode()
        if len(raw) > 4096 or self.progress_bytes + len(raw) > MAX_PROGRESS_BYTES:
            raise CaptureError('Progress byte limit')
        if self.total + len(raw) > MAX_TOTAL_BYTES - 8192:
            raise CaptureError('Evidence total byte limit')
        self._write(self.progress_fd, raw)
        self.progress_bytes += len(raw)

    def close(self):
        os.close(self.progress_fd)
        os.close(self.fd)


def run(platform, output, duration, clock=time.monotonic, sleep=time.sleep):
    if not 1 <= duration <= MAX_DURATION_SECONDS:
        raise ValueError('Use 1..7200 seconds')
    started = clock()
    end = started + duration
    gate = JournalGate(platform.boot, int(started * 1000000))
    polls = incidents = warnings = capped = 0
    last_incident = None
    result = dict(status='ENDED', reason='DURATION_ENDED', motor_commands=0,
                  automatic_recovery=False, device_audio_opened=False,
                  boot_id=platform.boot, clock_source='boot monotonic, no wall-clock UTC assumption')
    try:
        owner = platform.check()
        output.write('run.json', dict(schema='aura-usb-readonly-incidents-1', pid=os.getpid(),
            owner=owner, started_mono_us=gate.started_us, requested_duration_s=duration,
            poll_seconds=POLL_SECONDS, maximum_incidents=MAX_INCIDENTS,
            minimum_incident_interval_s=INCIDENT_GAP_SECONDS, maximum_total_bytes=MAX_TOTAL_BYTES,
            message=WARNING, scope='metadata only, no audio/face payload, no recovery'), limit=8192)
        while clock() < end:
            turn = clock()
            owner = platform.check()
            raw = platform.journal()
            batch = gate.consume(raw, int(clock() * 1000000))
            polls += 1
            fresh = batch['new_warning_timestamps_us']
            warnings += len(fresh)
            capped += int(batch['sample_capped'])
            trigger = bool(fresh) and (last_incident is None or turn - last_incident >= INCIDENT_GAP_SECONDS)
            output.progress(dict(elapsed_s=round(clock() - started, 3), owner=owner,
                sampled_lines=batch['sampled_lines'], sample_capped=batch['sample_capped'],
                fresh_warning_count=len(fresh), filtered=batch['filtered'], incident_triggered=trigger))
            if trigger:
                last_incident = clock()
                if end - last_incident < 3.:
                    raise CaptureError('INSUFFICIENT_TIME_FOR_INCIDENT')
                captured = platform.capture(clock, sleep, end)
                output.write('incident-%03d.json' % (incidents + 1), dict(
                    boot_id=platform.boot, event=batch, owner_before=owner,
                    captured=captured, elapsed_s=round(clock() - started, 3)))
                incidents += 1
                if incidents >= MAX_INCIDENTS:
                    result['reason'] = 'MAX_INCIDENTS_RECORDED'
                    break
            sleep(max(0., min(POLL_SECONDS - (clock() - turn), end - clock())))
    except (Exception, KeyboardInterrupt) as exc:
        result.update(reason='CAPTURE_STOPPED_ON_ERROR', error=type(exc).__name__ + ': ' + str(exc)[:160])
    finally:
        result.update(elapsed_s=round(clock() - started, 3), polls=polls, incidents=incidents,
                      new_warning_timestamps=warnings, capped_journal_windows=capped,
                      bytes_before_final=output.total)
        output.write('result.json', result, limit=8192)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--duration', type=float, default=7200.)
    parser.add_argument('--camera-pid', type=int, required=True)
    parser.add_argument('--gui-pid', type=int, required=True)
    args = parser.parse_args()
    if not 1 <= args.duration <= 7200 or min(args.camera_pid, args.gui_pid) <= 1:
        parser.error('Finite 1..7200 duration and explicit current owner PIDs required')
    output = BoundedOutput(args.output)
    try:
        try:
            platform = Platform(args.camera_pid, args.gui_pid)
        except Exception as exc:
            result = dict(status='ENDED', reason='INITIAL_METADATA_READ_FAILED',
                          error=type(exc).__name__ + ': ' + str(exc)[:160],
                          motor_commands=0, automatic_recovery=False)
            output.write('result.json', result, limit=8192)
            print(json.dumps(result))
            return 1
        result = run(platform, output, args.duration)
        print(json.dumps(result))
        return int(result['reason'] == 'CAPTURE_STOPPED_ON_ERROR')
    finally:
        output.close()


if __name__ == '__main__':
    raise SystemExit(main())
