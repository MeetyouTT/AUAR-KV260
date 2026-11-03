"""One bounded physical face-edge session; no implicit retry or rearming."""
import time


def run_session(device, reference, controller, packets, session, epoch, *,
                duration_s=10., clock=time.monotonic, cancelled=lambda: False):
    if not 0 < duration_s <= 10:
        raise ValueError('Finite 0..10 second face observation required')
    events = []
    before = device.status()
    if (before['flags'] or before['lease_left_ms']
            or before['width_us'] != reference.reference_us
            or controller.pulse_us != reference.reference_us):
        raise RuntimeError('Stopped current command differs; no ARM')
    report = {'before': before, 'commands_accepted': 0, 'events': events,
              'mechanical_zero_calibrated': False, 'automatic_retry': False}
    started = clock()
    reason = 'TIME_LIMIT'
    try:
        device.confirm_and_arm(reference, session, epoch, authorized=True)
        for packet in packets:
            if cancelled():
                reason = 'OPERATOR_STOP'
                break
            if clock()-started >= duration_s:
                break
            # Never bind an observation from before the current ARM.
            stamp = packet.get('source_mono_ms')
            if type(stamp) is int and stamp/1000. < device.reference_time:
                continue
            status = controller.observe(packet, int(clock()*1000))
            events.append(dict(status, elapsed_ms=round((clock()-started)*1000, 3)))
            if controller.stopped:
                if (report['commands_accepted'] == 0 and controller.reason in
                        ('SOURCE_NO_TARGET', 'SOURCE_UNCONFIRMED', 'SOURCE_EXPIRED')):
                    # No PWM has been sent. Wait for fresh, newly confirmed faces
                    # without rearming hardware or moving the stopped reference.
                    events[-1]['waiting_without_output'] = True
                    controller = type(controller)(controller.boot, reference.reference_us,
                        polarity=controller.polarity, config=controller.config)
                    continue
                reason = controller.reason
                device.stop()
                break
            current = device.status()
            if current['reason'] or not current['armed']:
                reason = 'HARDWARE_PERMISSION_LOST'
                device.stop()
                break
            if not status['new_source']:
                continue
            if report['commands_accepted'] and status['reason'] == 'SAFE_ZONE_HOLD':
                report['finish'] = device.finish()
                reason = 'SAFE_ZONE_REACHED'
                break
            # In the safe zone even the PWM output remains disabled.
            if not report['commands_accepted'] and status['pulse_us'] == reference.reference_us:
                continue
            if not controller.config.minimum_us <= status['pulse_us'] <= controller.config.maximum_us:
                raise RuntimeError('Command outside observed physical range')
            ack = device.submit(status['pulse_us'], stamp/1000., freshness_s=.25, margin_s=.02)
            events[-1]['actuator'] = ack
            if ack['outcome'] != 'ACCEPTED':
                reason = 'COMMAND_'+ack['reason']
                device.stop()
                break
            report['commands_accepted'] += 1
        else:
            reason = 'STREAM_ENDED'
        if device.reference is not None:
            report['finish'] = device.finish()
        report['reason'] = reason
        return report
    finally:
        report['stopped'] = device.stop()
        report['elapsed_s'] = round(clock()-started, 3)

