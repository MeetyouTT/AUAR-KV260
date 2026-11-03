"""ByteTrack IoU/score association with an exact NumPy-only assignment.

The cost-limit dummy construction has the same unmatched penalty as LAPJV's
extend_cost=True, cost_limit=thresh. No greedy association or ReID fallback.
"""
import numpy as np


def linear_assignment(cost_matrix, thresh):
    cost_matrix = np.asarray(cost_matrix, dtype=float)
    m, n = cost_matrix.shape
    if not m or not n:
        return np.empty((0, 2), dtype=int), tuple(range(m)), tuple(range(n))
    if not np.all(np.isfinite(cost_matrix)) or not 0 < thresh <= 1:
        raise ValueError('Invalid assignment cost')
    if max(m, n) > 64:
        raise ValueError('Assignment exceeds bounded track capacity')
    size = m + n
    matrix = np.full((size, size), thresh / 2., dtype=float)
    matrix[:m, :n] = np.where(cost_matrix <= thresh, cost_matrix, 1e6)
    matrix[m:, n:] = 0.
    # Shortest augmenting path Hungarian algorithm for a square cost matrix.
    u, v = np.zeros(size + 1), np.zeros(size + 1)
    p, way = np.zeros(size + 1, dtype=int), np.zeros(size + 1, dtype=int)
    for i in range(1, size + 1):
        p[0] = i
        j0 = 0
        minimum = np.full(size + 1, np.inf)
        used = np.zeros(size + 1, dtype=bool)
        while True:
            used[j0] = True
            i0 = p[j0]
            remaining = np.flatnonzero(~used[1:]) + 1
            reduced = matrix[i0 - 1, remaining - 1] - u[i0] - v[remaining]
            improved = reduced < minimum[remaining]
            changed = remaining[improved]
            minimum[changed] = reduced[improved]
            way[changed] = j0
            j1 = int(remaining[np.argmin(minimum[remaining])])
            delta = minimum[j1]
            u[p[used]] += delta
            v[used] -= delta
            minimum[~used] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            previous = way[j0]
            p[j0] = p[previous]
            j0 = previous
    matches = [(int(p[j] - 1), j - 1) for j in range(1, n + 1)
               if 0 < p[j] <= m and cost_matrix[p[j] - 1, j - 1] <= thresh]
    output = np.asarray(matches, dtype=int).reshape(-1, 2)
    return output, tuple(i for i in range(m) if i not in set(output[:, 0])), tuple(j for j in range(n) if j not in set(output[:, 1]))


def iou_distance(atracks, btracks):
    if not atracks or not btracks:
        return np.ones((len(atracks), len(btracks)))
    a = np.asarray([t if isinstance(t, np.ndarray) else t.tlbr for t in atracks], dtype=float)
    b = np.asarray([t if isinstance(t, np.ndarray) else t.tlbr for t in btracks], dtype=float)
    # Preserve the author's cython_bbox inclusive-edge overlap convention.
    lengths = np.maximum(0., np.minimum(a[:, None, 2:], b[None, :, 2:]) - np.maximum(a[:, None, :2], b[None, :, :2]) + 1.)
    intersection = lengths.prod(axis=2)
    area_a = np.maximum(0., a[:, 2:] - a[:, :2] + 1.).prod(axis=1)
    area_b = np.maximum(0., b[:, 2:] - b[:, :2] + 1.).prod(axis=1)
    return 1. - intersection / np.maximum(area_a[:, None] + area_b[None, :] - intersection, 1e-12)


def fuse_score(cost_matrix, detections):
    if not cost_matrix.size:
        return cost_matrix
    return 1. - (1. - cost_matrix) * np.asarray([d.score for d in detections])[None, :]
