"""Plain JSON statistics, including NumPy-derived mouth activity values."""
def summarize(samples):
    intervals=sorted(float(row['interval_ms']) for row in samples if row['interval_ms'] is not None)
    return {'samples':len(samples),'max_interval_ms':max(intervals,default=0.),
            'p95_interval_ms':intervals[int((len(intervals)-1)*.95)] if intervals else 0.,
            'intervals_over_100ms':sum(value>100 for value in intervals),
            'blink_samples':sum(bool(row['blink_active']) for row in samples),
            'speech_blink_samples':sum(bool(row['blink_active'] and row['playing']) for row in samples),
            'speech_open_mouth_samples':sum(bool(row['playing'] and row['speech_gain']>.1 and row['mouth_level']>.1) for row in samples)}
