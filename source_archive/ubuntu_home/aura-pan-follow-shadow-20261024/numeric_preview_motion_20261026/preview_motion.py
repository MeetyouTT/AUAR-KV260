"""Read-only cached-preview motion observer. Images stay in memory; no actuator API."""
import json
import math
import threading
import time
import urllib.parse
import urllib.request

import cv2
import numpy as np


def background_mask(shape, face_boxes=()):
    h, w = shape
    mask = np.full((h, w), 255, np.uint8)
    # Reject the usual central person/body foreground, plus overlay borders.
    mask[int(h * .08):, int(w * .30):int(w * .70)] = 0
    mask[:8, :] = mask[-8:, :] = 0
    mask[:, :8] = mask[:, -8:] = 0
    for x, y, fw, fh in face_boxes:
        x, y, fw, fh = (v / 2. for v in (x, y, fw, fh))
        pad = max(12., fw * .4)
        left, right = max(0, int(x - pad)), min(w, int(x + fw + pad) + 1)
        top, bottom = max(0, int(y - max(12., fh * .4))), min(h, int(y + fh * 1.4) + 1)
        mask[top:bottom, left:right] = 0
    return mask


def spread(points, shape):
    if len(points) == 0:
        return 0, 0., 0.
    h, w = shape
    cells = {(min(3, int(x / w * 4)), min(2, int(y / h * 3))) for x, y in points}
    return len(cells), float(np.ptp(points[:, 0]) / w), float(np.ptp(points[:, 1]) / h)


class BackgroundMotion:
    """All later images are compared to the FIRST valid image, never a rolling anchor."""
    def __init__(self):
        self.anchor = self.points = self.anchor_meta = None
        self.last_key = None

    def process(self, gray640, metadata, face_boxes=()):
        result = {k: metadata[k] for k in ('board_boot_id', 'camera_epoch', 'frame_id',
                                          'captured_mono_ms', 'sample_mono_s')}
        result.update(state='UNMEASURABLE', reason='', dx_px=None, dy_px=None,
                      pixel_coordinate_space='640x480 mirrored cached preview', face_boxes_masked=len(face_boxes))
        if gray640 is None or gray640.shape != (480, 640) or gray640.dtype != np.uint8:
            result['reason'] = 'INVALID_PREVIEW_GEOMETRY'
            return result
        key = (metadata['board_boot_id'], metadata['camera_epoch'], metadata['frame_id'])
        if key == self.last_key:
            result['reason'] = 'DUPLICATE_FRAME'
            return result
        if self.anchor_meta and (key[:2] != self.last_key[:2]
                                 or metadata['captured_mono_ms'] <= self.anchor_meta['captured_mono_ms']):
            result['reason'] = 'CONTEXT_CHANGED_OR_OLD_CAPTURE'
            return result
        self.last_key = key
        gray = cv2.resize(gray640, (320, 240), interpolation=cv2.INTER_AREA)
        mask = background_mask(gray.shape, face_boxes)
        if self.anchor is None:
            self.anchor, self.anchor_meta = gray.copy(), dict(result)
            found = cv2.goodFeaturesToTrack(gray, maxCorners=160, qualityLevel=.02, minDistance=8, mask=mask)
            self.points = np.empty((0, 1, 2), np.float32) if found is None else found
            cells, sx, sy = spread(self.points.reshape(-1, 2), gray.shape)
            result.update(reason='FIRST_FRAME_BASELINE', reference_frame_id=metadata['frame_id'],
                          corners=len(self.points), spatial_cells=cells, span_x_ratio=sx, span_y_ratio=sy)
            if len(self.points) >= 20 and cells >= 4 and sx >= .30 and sy >= .25:
                result['state'] = 'BASELINE_READY'
            else:
                result['reason'] = 'INSUFFICIENT_BASELINE_TEXTURE'
            return result
        result.update(reference_frame_id=self.anchor_meta['frame_id'],
                      reference_captured_mono_ms=self.anchor_meta['captured_mono_ms'], corners=len(self.points))
        if len(self.points) < 20:
            result['reason'] = 'INSUFFICIENT_BASELINE_TEXTURE'
            return result
        options = dict(winSize=(21, 21), maxLevel=2,
                       criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 25, .02))
        forward, ok1, errors = cv2.calcOpticalFlowPyrLK(self.anchor, gray, self.points, None, **options)
        if forward is None:
            result['reason'] = 'LK_NO_TRACKS'
            return result
        backward, ok2, _ = cv2.calcOpticalFlowPyrLK(gray, self.anchor, forward, None, **options)
        if backward is None:
            result['reason'] = 'LK_NO_REVERSE_TRACKS'
            return result
        a, b = self.points.reshape(-1, 2), forward.reshape(-1, 2)
        fb = np.linalg.norm(backward.reshape(-1, 2) - a, axis=1)
        finite = np.isfinite(b).all(axis=1) & np.isfinite(fb)
        xy = np.rint(np.where(np.isfinite(b), b, -1)).astype(np.int32)
        inside = (xy[:, 0] >= 0) & (xy[:, 0] < 320) & (xy[:, 1] >= 0) & (xy[:, 1] < 240)
        allowed = np.zeros(len(a), bool)
        allowed[inside] = mask[xy[inside, 1], xy[inside, 0]] > 0
        good = finite & inside & allowed & (ok1.ravel() > 0) & (ok2.ravel() > 0) & (fb <= .75) & (errors.ravel() <= 25.)
        aa, bb = a[good], b[good]
        result.update(tracked_background_points=len(aa), median_fb_error_px320=float(np.median(fb[good])) if good.any() else None)
        if len(aa) < 20:
            result['reason'] = 'INSUFFICIENT_BACKGROUND_TRACKS'
            return result
        affine, selected = cv2.estimateAffinePartial2D(aa, bb, method=cv2.RANSAC,
            ransacReprojThreshold=1.5, maxIters=1000, confidence=.99, refineIters=10)
        if affine is None or selected is None:
            result['reason'] = 'NO_BACKGROUND_CONSENSUS'
            return result
        inlier = selected.ravel().astype(bool)
        cells, sx, sy = spread(aa[inlier], gray.shape)
        ratio = float(np.mean(inlier))
        scale = float(math.hypot(affine[0, 0], affine[1, 0]))
        rotation = float(math.degrees(math.atan2(affine[1, 0], affine[0, 0])))
        flow = bb[inlier] - aa[inlier]
        shift = np.median(flow, axis=0)
        residual = np.linalg.norm(flow - shift, axis=1)
        result.update(inliers=int(inlier.sum()), inlier_ratio=ratio, spatial_cells=cells,
                      span_x_ratio=sx, span_y_ratio=sy, affine_scale=scale, affine_rotation_degrees=rotation,
                      median_flow_residual_px320=float(np.median(residual)))
        if not (inlier.sum() >= 20 and ratio >= .65 and cells >= 4 and sx >= .30 and sy >= .25
                and .95 <= scale <= 1.05 and abs(rotation) <= 3. and np.median(residual) <= 1.5):
            result['reason'] = 'BACKGROUND_QUALITY_REJECTED'
            return result
        result.update(state='MEASURED_BACKGROUND_SHIFT', reason='FIXED_BASELINE_LK_FB_RANSAC',
                      dx_px=float(shift[0] * 2.), dy_px=float(shift[1] * 2.))
        return result


class CachedPreviewFetcher:
    def __init__(self, base_url, timeout_s=.35):
        parts = urllib.parse.urlsplit(base_url)
        if parts.scheme != 'http' or parts.hostname not in ('127.0.0.1', 'localhost') or parts.path not in ('', '/'):
            raise ValueError('Use the board-local cached HTTP preview only')
        self.base, self.timeout = base_url.rstrip('/'), timeout_s
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def get(self, path, limit):
        with self.opener.open(self.base + path, timeout=self.timeout) as response:
            data, headers = response.read(limit + 1), dict(response.headers)
        if len(data) > limit:
            raise ValueError('PREVIEW_RESPONSE_TOO_LARGE')
        return data, {k.lower(): v for k, v in headers.items()}

    def __call__(self):
        raw, _ = self.get('/v1/ui/status', 131072)
        status = json.loads(raw)
        p = status['preview']
        boot, epoch, fid, stamp = status['board_boot_id'], p['camera_epoch'], p['frame_id'], p['captured_mono_ms']
        if (not isinstance(boot, str) or not isinstance(epoch, str) or type(fid) is not int or type(stamp) is not int
                or not 0 <= status['observed_mono_ms'] - stamp < 1000):
            raise ValueError('INVALID_CACHED_FRAME_REFERENCE')
        query = urllib.parse.urlencode(dict(camera_epoch=epoch, frame_id=fid))
        jpeg, headers = self.get('/v1/ui/preview.jpg?' + query, 2 * 1024 * 1024)
        if (headers.get('x-aura-boot-id') != boot or headers.get('x-aura-camera-epoch') != epoch
                or headers.get('x-aura-frame-id') != str(fid)):
            raise ValueError('PREVIEW_HEADER_REFERENCE_MISMATCH')
        gray = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_GRAYSCALE)
        boxes = []
        try:
            face_raw, _ = self.get('/v1/motion/face/observation', 32768)
            face = json.loads(face_raw)
            box = (face.get('target') or {}).get('box')
            if (face.get('state') == 'READY' and face.get('target_kind') == 'face'
                    and face.get('board_boot_id') == boot and face.get('camera_epoch') == epoch
                    and type(face.get('source_mono_ms')) is int and abs(face['source_mono_ms'] - stamp) <= 250
                    and isinstance(box, list) and len(box) == 4
                    and all(type(v) in (int, float) and math.isfinite(v) for v in box) and box[2] > 0 and box[3] > 0):
                boxes = [box]
        except (OSError, ValueError, KeyError):
            pass  # Central foreground mask and spatial-consensus checks remain.
        metadata = dict(board_boot_id=boot, camera_epoch=epoch, frame_id=fid,
                        captured_mono_ms=stamp, sample_mono_s=time.monotonic())
        return gray, metadata, boxes


class PreviewMotionObserver:
    def __init__(self, base_url='http://127.0.0.1:8790', *, duration_s=8., interval_s=.25, fetch=None):
        if not (type(duration_s) in (int, float) and 0 < duration_s <= 15
                and type(interval_s) in (int, float) and .2 <= interval_s <= .25):
            raise ValueError('Bounded duration <=15s and 0.2..0.25s interval required')
        cv2.setNumThreads(1)  # This observer process only; no camera/control service changes.
        self.fetch = fetch or CachedPreviewFetcher(base_url)
        self.duration, self.interval = duration_s, interval_s
        self.stop_event, self.ready = threading.Event(), threading.Event()
        self.ready_event = self.ready
        self.lock = threading.Lock()
        self.results, self.baseline, self.thread = [], None, None
        self.final_reason = 'NOT_STARTED'

    def start(self):
        if self.thread is not None:
            raise RuntimeError('Observer is single-use')
        self.thread = threading.Thread(target=self._work, name='cached-preview-motion', daemon=True)
        self.thread.start()
        return self

    def wait_for_baseline(self, timeout_s=.8):
        return self.ready.wait(timeout_s)

    def wait_baseline(self, timeout_s=2.):
        if not 0 <= timeout_s <= 2:
            raise ValueError('Bounded baseline wait required')
        return self.ready.wait(timeout_s)

    def _work(self):
        measurement = BackgroundMotion()
        end = time.monotonic() + self.duration
        try:
            while not self.stop_event.is_set() and time.monotonic() < end and len(self.results) < 76:
                began = time.monotonic()
                try:
                    gray, metadata, boxes = self.fetch()
                    value = measurement.process(gray, metadata, boxes)
                    if measurement.anchor is not None and self.baseline is None:
                        with self.lock: self.baseline = dict(value)
                        self.ready.set()
                except Exception as error:
                    value = dict(state='UNMEASURABLE', reason='FETCH_OR_PROCESS_' + type(error).__name__,
                                 sample_mono_s=time.monotonic(), dx_px=None, dy_px=None)
                value['processing_wall_ms'] = (time.monotonic() - began) * 1000.
                with self.lock: self.results.append(value)
                self.stop_event.wait(max(0., self.interval - (time.monotonic() - began)))
            self.final_reason = 'STOP_REQUESTED' if self.stop_event.is_set() else 'DURATION_COMPLETE'
        finally:
            measurement.anchor = measurement.points = None

    def snapshot(self):
        with self.lock:
            rows = [dict(r) for r in self.results]
            baseline = dict(self.baseline) if self.baseline else None
        measured = [r for r in rows if r['state'] == 'MEASURED_BACKGROUND_SHIFT']
        return dict(scope='NUMERIC_CACHED_PREVIEW_BACKGROUND_DISPLACEMENT', images_saved=False,
                    actuator_access=False, samples=rows, baseline=baseline, measured_samples=len(measured),
                    maximum_abs_dx_px=max((abs(r['dx_px']) for r in measured), default=None),
                    maximum_abs_dy_px=max((abs(r['dy_px']) for r in measured), default=None),
                    observation_state='MEASURED' if measured else 'UNMEASURABLE',
                    observer_alive=self.thread.is_alive() if self.thread else False, final_reason=self.final_reason,
                    caveat='Background image displacement, not measured shaft angle or proof of servo power')

    def close_after_stop(self, stopped_readback, timeout_s=1.):
        if (not isinstance(stopped_readback, dict) or stopped_readback.get('flags') != 0
                or stopped_readback.get('lease_left_ms') != 0 or stopped_readback.get('reason', 0) != 0):
            raise ValueError('Actual STOP readback required before observer join')
        if not 0 <= timeout_s <= 1:
            raise ValueError('Bounded observer join required')
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout_s)
        result = self.snapshot()
        result['close_after_output_stop'] = True
        return result
