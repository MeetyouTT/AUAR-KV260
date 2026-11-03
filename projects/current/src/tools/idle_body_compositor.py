"""Existing idle frames and tracked local mouths; no generated body movement."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops
from tools.pillow_compat import AFFINE
BILINEAR=getattr(Image,'Resampling',Image).BILINEAR

from board.interaction.avatar_player import AvatarPlayer
from tools.mouth_compositor import mouth_mask

AURA = Path(__file__).resolve().parents[1]
BLINK = AURA.parent / 'deliverables/2026-10-06_voice_blink'
IDENTITY = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]


def material_variant(generation, count):
    """Stable on both renderers; consecutive two-step talk generations vary."""
    generation=max(0,int(generation))
    return (generation ^ (generation >> 1)) % max(1,int(count))


def seed_speaking_materials(core, generation, now):
    """Choose an existing semantic-equivalent mouth pool at the turn boundary."""
    if not all(hasattr(core,name) for name in ('pool','_pool_i','_asset_of','_asset_t0')):return
    for state in ('SPEAKING_NEUTRAL','SPEAKING','SPEAKING_LOW'):
        names=core.pool(state)
        if len(names)>1:
            index=material_variant(generation,len(names))
            core._pool_i[state]=index;core._asset_of[state]=names[index];core._asset_t0[state]=now


def eye_centres(path, bounds):
    """Recover static anchor registration from the existing paired eye masks."""
    with Image.open(path) as image:
        alpha = np.asarray(image.getchannel('A'), dtype=float)
    y, x = np.mgrid[:alpha.shape[0], :alpha.shape[1]]
    result = []
    for side in (x < alpha.shape[1] / 2, x >= alpha.shape[1] / 2):
        weights = alpha * side
        total = weights.sum()
        if total <= 0: raise ValueError('Missing registered eye mask')
        result.append([float((weights*x).sum()/total)+bounds[0],
                       float((weights*y).sum()/total)+bounds[1]])
    return np.asarray(result)


def similarity(source, target):
    v, w = source[1]-source[0], target[1]-target[0]
    norm = float(v@v)
    if norm <= 1e-8:
        raise ValueError('Coincident eye registration points')
    a = float(v@w)/norm
    b = float(v[0]*w[1]-v[1]*w[0])/norm
    rotation = np.array([[a, -b], [b, a]])
    translation = target[0]-rotation@source[0]
    return np.column_stack((rotation, translation))


class IdleBodyTrack:
    """Keep the production idle player running across speech and mouth pools."""
    FAMILIES = {'talking_calm_reuse_v1': 'idle_normal',
                'talking_calm_reuse_v1_b': 'idle_normal',
                'talking_high_reuse_v1': 'talking_normal',
                'talking_high_reuse_v1_b': 'talking_normal',
                'talking_low_reuse_v1': 'talking_low'}

    BODY_STATES={'idle_normal':'IDLE','idle_present':'PRESENT',
                 'talking_normal':'SPEAKING','talking_low':'SPEAKING_LOW'}

    def __init__(self, core, *, expressive=False):
        self.core = core
        self.expressive=bool(expressive)
        self.current_family='idle_normal'
        self.player = AvatarPlayer(sprite_root=core.sprite_root)
        self.player.idle_gain = 0.0
        native=getattr(core,'native_pixels',None)
        if native:self.player.blend_frames=native.materialize_blend
        profile = json.loads((BLINK/'blink_profile.json').read_text(encoding='utf-8'))
        self.poses = profile['targets']['idle_normal']['poses']
        self.pose_tracks={name:profile['targets'][name]['poses'] for name in self.BODY_STATES}
        bounds = profile['bounds']
        centres = {name: eye_centres(BLINK/data['layers'][3]['file'], bounds)
                   for name, data in profile['targets'].items() if name in set(self.BODY_STATES)}
        self.to_idle = {name: similarity(points, centres['idle_normal'])
                        for name, points in centres.items()}
        self.to_idle['idle_normal'] = np.asarray(IDENTITY)
        self.to_family={(source,target):similarity(centres[source],centres[target])
                        for source in set(self.FAMILIES.values()) for target in self.BODY_STATES}
        if self.expressive:
            # Other variants lack matching pose tracks. Preserve their existing
            # use elsewhere, but never put an unregistered body under this face.
            for family,state in self.BODY_STATES.items():self.player._pool_names[state]=(family,)

    def reset(self):
        self.player.reset_playback()

    def _ensure_family(self, family):
        state=self.BODY_STATES[family];key=(state,family)
        if key not in self.player._seq_cache:
            sequence=self.core.sequence(state,asset=family)
            if sequence is None or len(sequence[0])!=len(self.pose_tracks[family]):
                raise ValueError('Body frames and registered face track do not match: '+family)
            self.player._seq_cache[key]=sequence
            self.player._sop_cache[key]=self.core.sop(state,asset=family)

    def warmup(self):
        if self.expressive:
            for family in self.BODY_STATES:self._ensure_family(family)

    def family_for(self, asset, generation):
        if asset in ('talking_calm_reuse_v1','talking_calm_reuse_v1_b'):
            return ('idle_normal','idle_present')[material_variant(generation,2)]
        return self.FAMILIES.get(asset,'idle_normal')

    def sample(self, now, *, asset=None, generation=0):
        if self.expressive:
            family=self.family_for(asset,generation);self._ensure_family(family)
            self.player.reply_text=self.core.reply_text
            self.player.emotion=self.core.emotion
            meta=self.player.display_frame(self.BODY_STATES[family],now)
            actual=meta['asset'];self.current_family=actual
            if actual not in self.pose_tracks:raise ValueError('Unregistered displayed body: '+actual)
            poses=self.pose_tracks[actual];position=meta['source_position']
            left=min(int(position),len(poses)-1);right=min(left+1,len(poses)-1);fraction=position-left
            matrix=(1-fraction)*np.asarray(poses[left]['matrix'])+fraction*np.asarray(poses[right]['matrix'])
            return meta,matrix
        # Share decoded idle frames with the preview rather than load a second copy.
        if not self.player._seq_cache:
            sequence = self.core.sequence('IDLE')
            if sequence is None or len(sequence[0]) != len(self.poses):
                raise ValueError('Idle body frames and face tracking do not match')
            self.player._seq_cache[('IDLE', sequence[3])] = sequence
            self.player._sop_cache[('IDLE', sequence[3])] = self.core.sop('IDLE')
        meta = self.player.frame_at('IDLE', now)
        position = meta['source_position']
        left = min(int(position), len(self.poses)-1)
        right = min(left+1, len(self.poses)-1)
        fraction = position-left
        matrix = ((1-fraction)*np.asarray(self.poses[left]['matrix'])
                  + fraction*np.asarray(self.poses[right]['matrix']))
        return meta, matrix

    def mouth_matrix(self, asset, face_matrix):
        source = (self.to_family[(self.FAMILIES[asset],self.current_family)] if self.expressive
                  else self.to_idle[self.FAMILIES[asset]])
        return (np.vstack((face_matrix, [0, 0, 1]))
                @ np.vstack((source, [0, 0, 1])))[:2].tolist()


def mouth_patch(source, matrix, gain):
    """Warp only the protected mouth ROI to its tracked position in an idle frame."""
    gain = max(0.0, min(1.0, float(gain)))
    if gain == 0: return None
    box = mouth_mask().getbbox()
    patch = source.crop(box)
    coverage = ImageChops.multiply(mouth_mask().crop(box), patch.getchannel('A'))
    if gain != 1: coverage = coverage.point([round(i*gain) for i in range(256)])
    patch.putalpha(coverage)
    m = np.asarray(matrix, dtype=float)
    corners = np.array([[box[0], box[1], 1], [box[2], box[1], 1],
                        [box[2], box[3], 1], [box[0], box[3], 1]])@m.T
    left, top = max(0, math.floor(corners[:,0].min())-2), max(0, math.floor(corners[:,1].min())-2)
    right, bottom = min(source.width, math.ceil(corners[:,0].max())+2), min(source.height, math.ceil(corners[:,1].max())+2)
    ma,mb,mc=m[0];md,me,mf=m[1];det=ma*me-mb*md
    if abs(det)<1e-8:raise ValueError('Singular tracked mouth transform')
    a,b,c,d,e,f=me/det,-mb/det,(mb*mf-me*mc)/det,-md/det,ma/det,(md*mc-ma*mf)/det
    affine = (a, b, c+a*left+b*top-box[0], d, e, f+d*left+e*top-box[1])
    return patch.transform((right-left, bottom-top), AFFINE,
                           affine, BILINEAR), (left, top)


def composite_idle_mouth(body, source, matrix, gain):
    patch = mouth_patch(source, matrix, gain)
    if patch is None: return body
    result = body.copy()
    result.alpha_composite(*patch)
    result.putalpha(body.getchannel('A'))
    return result
