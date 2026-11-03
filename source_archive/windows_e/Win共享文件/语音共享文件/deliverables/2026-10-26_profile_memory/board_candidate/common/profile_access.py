"""Revocable, process-local grants issued only by authenticated local control.

Names, face matches and speaker candidates are never credentials. Restarting
the service requires a new local selection, while stored facts remain durable.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import hmac
import re
import secrets
import threading
import time


def identifier(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{32}',value):
        raise ValueError('Invalid profile identifier')
    return value


def actor(meta):
    values=tuple(meta.get(k) for k in ('board_boot_id','session_id'))
    if any(not isinstance(v,str) or not re.fullmatch('[A-Za-z0-9_-]{1,96}',v) for v in values):
        raise ValueError('Invalid profile device/session')
    return values


@dataclass(frozen=True)
class ProfileGrant:
    profile_id: str
    actor: tuple
    nonce: str
    until: float


class ProfileAccess:
    def __init__(self,control_key=None,*,verifier=None,clock=time.monotonic):
        if control_key is not None and (not isinstance(control_key,str) or not re.fullmatch('[0-9a-f]{64}',control_key)):
            raise ValueError('Invalid local control credential')
        if verifier is not None and (not isinstance(verifier,str) or not re.fullmatch('[0-9a-f]{64}',verifier)):
            raise ValueError('Invalid local control verifier')
        self.verifier=hashlib.sha256(control_key.encode()).hexdigest() if control_key else verifier
        self.clock=clock;self.lock=threading.RLock();self.grants={}

    def authenticate(self,key):
        if (not self.verifier or not isinstance(key,str) or not re.fullmatch('[0-9a-f]{64}',key)
                or not hmac.compare_digest(hashlib.sha256(key.encode()).hexdigest(),self.verifier)):
            raise PermissionError('Local profile control is unavailable or unauthorized')

    def issue(self,profile_id,meta,*,ttl=900):
        identifier(profile_id);device=actor(meta)
        if type(ttl) is not int or not 30<=ttl<=1800:raise ValueError('Profile grant lifetime must be 30..1800 seconds')
        with self.lock:
            self.revoke(meta)
            now=self.clock()
            self.grants={k:v for k,v in self.grants.items() if v.until>now}
            if len(self.grants)>=32:raise ValueError('Too many active profile selections')
            token=secrets.token_hex(32)
            grant=ProfileGrant(profile_id,device,secrets.token_hex(16),now+ttl)
            self.grants[hashlib.sha256(token.encode()).hexdigest()]=grant
            return token,grant

    def revoke(self,meta):
        device=actor(meta)
        with self.lock:
            for key,grant in list(self.grants.items()):
                if grant.actor==device:del self.grants[key]

    def resolve(self,token,meta):
        if not isinstance(token,str) or not re.fullmatch('[0-9a-f]{64}',token):
            raise PermissionError('Invalid profile credential')
        with self.lock:
            grant=self.grants.get(hashlib.sha256(token.encode()).hexdigest())
            if grant is None or grant.actor!=actor(meta):raise PermissionError('Profile credential belongs to another interaction')
            self._check(grant)
            return grant

    def _check(self,grant):
        if (not isinstance(grant,ProfileGrant) or self.clock()>=grant.until
                or not any(value is grant for value in self.grants.values())):
            raise PermissionError('Profile selection expired or was revoked')

    @contextmanager
    def use(self,grant):
        # Selection changes serialize with a bounded database operation. Long
        # inference/audio delivery never retains this lock.
        with self.lock:
            self._check(grant)
            yield grant.profile_id

    def health(self):
        return {'version':1,'configured':bool(self.verifier),'selection':'authenticated_local_control',
                'operator_credential_storage':'sha256_verifier_only',
                'grant_lifetime_max_seconds':1800,'restart_requires_selection':True,
                'automatic_speaker_unlock':False}
