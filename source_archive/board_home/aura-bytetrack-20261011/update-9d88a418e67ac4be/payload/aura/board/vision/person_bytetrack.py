"""Actual-observation wrapper around pinned ByteTrack, with bounded lifetimes."""
import hashlib
import math
from pathlib import Path
from types import SimpleNamespace


def verify_sources(config):
    directory = Path(__file__).resolve().parent / 'bytetrack'
    expected = config.get('source_sha256', {})
    if set(expected) != {'byte_tracker.py', 'kalman_filter.py', 'basetrack.py', 'matching.py', '__init__.py', 'LICENSE', 'upstream_manifest.json'}:
        raise ValueError('ByteTrack source manifest is incomplete')
    for name, digest in expected.items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('ByteTrack source hash mismatch: ' + name)


class PersonByteTracks:
    kind = 'BYTETRACK_PINNED_NUMPY'

    def __init__(self, epoch, config, verify=True):
        if verify:
            verify_sources(config)
        from .bytetrack.byte_tracker import BYTETracker
        self.epoch, self.config = epoch, dict(config)
        if (config['track_threshold'] != .5 or config['new_track_threshold'] != .6
                or config['match_threshold'] != .8 or config['nominal_hz'] != 10
                or config['lost_ms'] != 500 or config['confirm_observations'] != 2):
            raise ValueError('Unreviewed ByteTrack configuration')
        args = SimpleNamespace(track_thresh=.5, track_buffer=30000000, match_thresh=.8, mot20=False)
        self.tracker = BYTETracker(args, frame_rate=10)
        self.last_time = self.last_fid = None
        self.history, self.tracks = {}, {}
        self.selected_key = None
        self.manual_mode = False
        self.update_index = 0
        self.events = []

    @property
    def target_id(self):
        return self.selected_key[0] if self.selected_key else None

    @target_id.setter
    def target_id(self, value):
        track = self.tracks.get(value)
        if not track or not track['visible'] or not track['confirmed']:
            raise ValueError('Target is not currently confirmed')
        self.manual_mode = True
        self.selected_key = (value, track['generation'])

    def update(self, people, fid, stamp, width, height):
        import numpy as np
        if (not math.isfinite(stamp) or stamp < 0 or type(fid) is not int or fid < 1
                or (self.last_fid is not None and (fid <= self.last_fid or stamp <= self.last_time))):
            raise ValueError('ByteTrack source must advance')
        if len(people) > 16:
            raise ValueError('Too many person detections')
        self.update_index += 1
        self.events = []
        now_ms = round(stamp * 1000)
        # Expire by original source time before any association, even if an ID
        # could otherwise be rescued after a long inference/capture pause.
        stale = {tid for tid, row in self.history.items() if now_ms - row['stamp_ms'] > self.config['lost_ms']}
        for name in ('tracked_stracks', 'lost_stracks'):
            collection = getattr(self.tracker, name)
            expired = [t for t in collection if t.track_id in stale]
            for track in expired:
                track.mark_removed()
                self.events.append({'event': 'ENDED', 'track_id': track.track_id})
            setattr(self.tracker, name, [t for t in collection if t.track_id not in stale])
        dt = 1. if self.last_time is None else (stamp - self.last_time) * self.config['nominal_hz']
        # When all old tracks have ended, a large source gap starts a fresh
        # lifecycle rather than being fed into a giant prediction step.
        self.tracker.kalman_filter.set_dt(min(dt, 10.))
        rows = []
        for d in people:
            x, y, w, h = d.box
            if d.label != 'person' or min(w, h) <= 0 or not all(math.isfinite(v) for v in d.box + (d.score,)):
                raise ValueError('Invalid person tracking input')
            rows.append([x, y, x+w, y+h, d.score])
        output = self.tracker.update(np.asarray(rows, dtype=float).reshape(-1, 5), (height, width), (height, width))
        current = {}
        for t in output:
            if not t.is_activated or t.frame_id != self.tracker.frame_id:
                continue
            tid = int(t.track_id)
            old = self.history.get(tid)
            consecutive = old is not None and old['index'] == self.update_index - 1
            generation = old['generation'] if consecutive else (old['generation'] + 1 if old else 1)
            seen = old['seen'] + 1 if consecutive else 1
            # Kalman predictions are for association; published geometry is
            # the current detection's actual measurement, never a lost box.
            x, y, w, h = (float(v) for v in t.observed_tlwh)
            right, bottom = min(width, x+w), min(height, y+h)
            x, y = max(0., x), max(0., y)
            w, h = right-x, bottom-y
            if min(w, h) <= 0:
                continue
            center = x + w/2.
            velocity = (center-old['center']) / (stamp-old['stamp_ms']/1000.) if consecutive else 0.
            row = {'track_id': tid, 'generation': generation, 'box': [x,y,w,h], 'score': float(t.score),
                'visible': True, 'confirmed': seen >= 2, 'frame_id': fid, 'captured_at': stamp,
                'velocity': [velocity, 0.], 'state': 'CONFIRMED' if seen >= 2 else 'NEW'}
            current[tid] = row
            self.history[tid] = {'generation': generation, 'seen': seen, 'index': self.update_index,
                'stamp_ms': now_ms, 'center': center}
            if not consecutive:
                self.events.append({'event': 'REACQUIRED' if old else 'ENTERED', 'track_id': tid, 'generation': generation})
        for tid in set(self.tracks) - set(current):
            self.events.append({'event': 'LOST', 'track_id': tid, 'generation': self.tracks[tid]['generation']})
        self.tracks = current
        if self.selected_key:
            tid, generation = self.selected_key
            t = current.get(tid)
            if not t or not t['confirmed'] or t['generation'] != generation:
                self.selected_key = None
        confirmed = [t for t in current.values() if t['confirmed']]
        if not self.manual_mode:
            self.selected_key = ((confirmed[0]['track_id'], confirmed[0]['generation']) if len(confirmed) == 1 else None)
        retained = {t.track_id for t in self.tracker.tracked_stracks + self.tracker.lost_stracks} | set(current)
        self.history = {k:v for k,v in self.history.items() if k in retained}
        if len(retained) > 64:
            raise RuntimeError('ByteTrack retained capacity exceeded')
        self.last_time, self.last_fid = stamp, fid
        return {'tracks': list(current.values()), 'target_id': self.target_id,
                'association': self.kind, 'events': list(self.events)}
