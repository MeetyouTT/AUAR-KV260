# -*- coding: utf-8 -*-
"""Event Envelope 与有界 Event Bus（Week A1 · 9/2 任务）

合同（人3 任务书 §五）：
  1. Event Bus 使用有界队列；
  2. 视觉帧可丢旧保新（LATEST）；
  3. 错误、取消和最终状态不能静默丢失（CRITICAL）；
  4. 满队列行为明确：丢弃/挤兑均可见（counters）。

线程模型：
  publish() 线程安全；
  dispatch_async=True   → 内部分发线程调用订阅者；
  dispatch_async=False  → 在 publish 调用线程同步分发（单测用，确定性高）。

移植说明：本实现对应板端 C++ 版的单一有界队列 + 策略入队 + 扇出分发，
接口与数据合同保持一致。
"""
import collections
import copy
import threading
import time
import typing
import uuid

from .events import EventType

Policy = typing.NewType("Policy", str)
POLICY_BOUNDED = "bounded"
POLICY_LATEST = "latest"
POLICY_CRITICAL = "critical"
# SCENE_STATE 是"最新最终状态"：允许新状态覆盖旧状态，但最新一份必须可读
POLICY_LATEST_FINAL = "latest_final"


class EventEnvelope:
    """事件信封：所有跨模块事件统一载体。

    字段：
      event_type    事件类型（EventType 常量）
      source        来源模块（如 "scene"、"audio_in"、"ui"）
      created_at_ms 创建时间戳（板端单调时钟，64 位）
      payload       事件载荷（dict，JSON 可序列化）
      event_id      全局唯一 ID（uuid hex）
      trace_id      可选链路追踪 ID（把请求→响应串起来）
      priority      参考优先级（不影响入队策略）
    """

    __slots__ = ("event_type", "source", "created_at_ms", "payload",
                 "event_id", "trace_id", "priority")

    def __init__(self, event_type: str, source: str, created_at_ms: int,
                 payload: typing.Optional[typing.Dict] = None,
                 event_id: typing.Optional[str] = None,
                 trace_id: typing.Optional[str] = None,
                 priority: int = 0) -> None:
        if not isinstance(event_type, str) or not event_type:
            raise ValueError("event_type 必须为非空字符串")
        self.event_type = event_type
        self.source = source or "unknown"
        self.created_at_ms = int(created_at_ms)
        self.payload = dict(payload) if payload else {}
        self.event_id = event_id or uuid.uuid4().hex
        self.trace_id = trace_id or ""
        self.priority = int(priority)

    def to_dict(self) -> typing.Dict:
        return {
            "event_type": self.event_type,
            "source": self.source,
            "created_at_ms": self.created_at_ms,
            "payload": copy.deepcopy(self.payload),
            "event_id": self.event_id,
            "trace_id": self.trace_id,
            "priority": self.priority,
        }

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return "<Event %s src=%s id=%s>" % (self.event_type, self.source, self.event_id[:8])


class BoundedQueue:
    """线程安全有界队列（支持按策略挤兑/删除）。

    内部用 deque，允许从中间删除元素（队列规模小，O(n) 可接受）。
    """

    def __init__(self, max_size: int) -> None:
        if max_size <= 0:
            raise ValueError("max_size 必须 > 0")
        self._items = collections.deque()
        self._max_size = max_size
        self._cv = threading.Condition()

    @property
    def max_size(self) -> int:
        return self._max_size

    def __len__(self) -> int:
        with self._cv:
            return len(self._items)

    def full(self) -> bool:
        with self._cv:
            return len(self._items) >= self._max_size

    def put(self, item: EventEnvelope) -> None:
        """阻塞入队（critical 兜底路径：绝不丢弃）。"""
        with self._cv:
            while len(self._items) >= self._max_size:
                self._cv.wait()
            self._items.append(item)
            self._cv.notify_all()

    def put_nowait(self, item: EventEnvelope) -> None:
        with self._cv:
            if len(self._items) >= self._max_size:
                raise RuntimeError("queue full")
            self._items.append(item)
            self._cv.notify_all()

    def evict_oldest_of_type(self, event_type: str) -> bool:
        """挤掉最旧的同类型事件（LATEST：丢旧保新）。成功返回 True。"""
        with self._cv:
            for i, it in enumerate(self._items):
                if it.event_type == event_type:
                    del self._items[i]
                    self._cv.notify_all()
                    return True
            return False

    def evict_oldest_noncritical(self, critical_types: typing.Set[str]) -> bool:
        """挤掉最旧的非 critical 事件（CRITICAL 兜底）。成功返回 True。"""
        with self._cv:
            for i, it in enumerate(self._items):
                if it.event_type not in critical_types:
                    del self._items[i]
                    self._cv.notify_all()
                    return True
            return False

    def evict_oldest_latest_final(self, latest_final_types: typing.Set[str]) -> bool:
        """挤掉最旧的非 latest_final 事件；若队列全为 latest_final，
        则挤掉最旧的 latest_final 自身（新状态覆盖旧状态）。"""
        with self._cv:
            # 第一优先：非 latest_final
            for i, it in enumerate(self._items):
                if it.event_type not in latest_final_types:
                    del self._items[i]
                    self._cv.notify_all()
                    return True
            # 第二优先：最旧的 latest_final（被新状态覆盖）
            for i, it in enumerate(self._items):
                if it.event_type in latest_final_types:
                    del self._items[i]
                    self._cv.notify_all()
                    return True
            return False

    def get(self) -> EventEnvelope:
        """阻塞取出队首。"""
        with self._cv:
            while not self._items:
                self._cv.wait()
            item = self._items.popleft()
            self._cv.notify_all()
            return item

    def get_nowait(self) -> EventEnvelope:
        with self._cv:
            if not self._items:
                raise RuntimeError("queue empty")
            item = self._items.popleft()
            self._cv.notify_all()  # 唤醒可能阻塞在 put 的发布线程
            return item

    def snapshot(self) -> typing.List[EventEnvelope]:
        """快照当前队列内容（测试/诊断用，不消费）。"""
        with self._cv:
            return list(self._items)


class Subscription:
    def __init__(self, bus: "EventBus", handler: typing.Callable[[EventEnvelope], None],
                 event_types: typing.Optional[typing.Set[str]]) -> None:
        self._bus = bus
        self.handler = handler
        self.event_types = event_types
        self._active = True

    @property
    def active(self) -> bool:
        return self._active

    def unsubscribe(self) -> None:
        self._bus._remove_subscription(self)
        self._active = False


class EventBus:
    """有界事件总线。

    构造参数：
      max_size         队列容量上限
      dispatch_async   是否启用内部分发线程（False=同步分发，单测确定性强）
      policies         事件类型 → 策略覆盖（默认按 events.py 自动映射）

    统计（证据可读）：
      published_count  成功入队数
      dropped_count    满队列被丢弃的事件数（按类型）
      evicted_count    为腾空间被挤掉的事件数（按类型）
      current_size     当前队列长度
    """

    def __init__(self, max_size: int = 128, dispatch_async: bool = False,
                 policies: typing.Optional[typing.Dict[str, str]] = None,
                 critical_types: typing.Optional[typing.Set[str]] = None,
                 now_ms_fn: typing.Optional[typing.Callable[[], int]] = None) -> None:
        self._queue = BoundedQueue(max_size)
        self._dispatch_async = dispatch_async
        self._now_ms = now_ms_fn or (lambda: int(time.time() * 1000))

        # 策略表
        self._policies = dict(policies) if policies else {}
        for t in EventType.LATEST_TYPES:
            self._policies.setdefault(t, POLICY_LATEST)
        for t in EventType.LATEST_FINAL_TYPES:
            self._policies.setdefault(t, POLICY_LATEST_FINAL)
        for t in EventType.CRITICAL_TYPES:
            self._policies.setdefault(t, POLICY_CRITICAL)
        self._critical_types = set(critical_types) if critical_types is not None else set(EventType.CRITICAL_TYPES)

        self._lock = threading.RLock()
        self._subscribers = []  # type: typing.List[Subscription]
        self._published = 0
        self._dropped = collections.Counter()
        self._evicted = collections.Counter()
        # 最近事件记录（wait_event/诊断用；事件已发生时直接可查）
        self._recent = collections.defaultdict(lambda: collections.deque(maxlen=64))
        self._dispatcher = None
        self._running = False
        if dispatch_async:
            self._running = True
            self._dispatcher = threading.Thread(target=self._run_dispatcher, daemon=True, name="event-bus")
            self._dispatcher.start()

    # ------------------------------------------------------------------ #
    # 发布
    # ------------------------------------------------------------------ #
    def publish(self, envelope: EventEnvelope) -> bool:
        """发布事件。返回 True 表示成功入队；False 表示被策略丢弃（有计数）。"""
        policy = self._policies.get(envelope.event_type, POLICY_BOUNDED)
        blocking_put = False
        with self._lock:
            if not self._queue.full():
                self._queue.put_nowait(envelope)
                self._published += 1
                ok = True
            elif policy == POLICY_LATEST:
                if self._queue.evict_oldest_of_type(envelope.event_type):
                    self._evicted[envelope.event_type] += 1
                    self._queue.put_nowait(envelope)
                    self._published += 1
                    ok = True
                else:  # 队列中没有同类型旧帧（异常：满但无同型），保守丢弃
                    self._dropped[envelope.event_type] += 1
                    ok = False
            elif policy == POLICY_LATEST_FINAL:
                if self._queue.evict_oldest_latest_final(EventType.LATEST_FINAL_TYPES):
                    self._evicted[envelope.event_type] += 1
                    self._queue.put_nowait(envelope)
                    self._published += 1
                    ok = True
                else:
                    self._dropped[envelope.event_type] += 1
                    ok = False
            elif policy == POLICY_CRITICAL:
                if self._queue.evict_oldest_noncritical(self._critical_types):
                    self._evicted[envelope.event_type] += 1
                    self._queue.put_nowait(envelope)
                    self._published += 1
                    ok = True
                else:
                    # 队列全部为 critical 且已满：阻塞等待空位，保证不丢
                    blocking_put = True
                    ok = True
            else:  # POLICY_BOUNDED
                self._dropped[envelope.event_type] += 1
                ok = False

        if blocking_put:
            self._queue.put(envelope)  # 阻塞在锁外
            with self._lock:
                self._published += 1

        if ok:
            self._record_recent(envelope)
            if not self._dispatch_async:
                self._dispatch_now(envelope)
        return ok

    def _record_recent(self, envelope: EventEnvelope) -> None:
        with self._lock:
            self._recent[envelope.event_type].append(envelope)


    # ------------------------------------------------------------------ #
    # 订阅
    # ------------------------------------------------------------------ #
    def subscribe(self, handler: typing.Callable[[EventEnvelope], None],
                  event_types: typing.Optional[typing.Iterable[str]] = None) -> Subscription:
        """注册订阅者。event_types=None 表示接收全部事件。"""
        if not callable(handler):
            raise ValueError("handler 必须可调用")
        types = set(event_types) if event_types is not None else None
        sub = Subscription(self, handler, types)
        with self._lock:
            self._subscribers.append(sub)
        return sub

    def _remove_subscription(self, sub: Subscription) -> None:
        with self._lock:
            if sub in self._subscribers:
                self._subscribers.remove(sub)

    def _dispatch_now(self, envelope: EventEnvelope) -> None:
        with self._lock:
            subs = list(self._subscribers)
        for sub in subs:
            if not sub.active:
                continue
            if sub.event_types is not None and envelope.event_type not in sub.event_types:
                continue
            try:
                sub.handler(envelope)
            except Exception:  # noqa: BLE001 - 订阅者异常不得中断总线
                self._dropped["__handler_error__"] += 1

    def _run_dispatcher(self) -> None:
        while self._running:
            try:
                env = self._queue.get()
            except Exception:  # noqa: BLE001
                continue
            self._dispatch_now(env)

    # ------------------------------------------------------------------ #
    # 测试/诊断辅助
    # ------------------------------------------------------------------ #
    def wait_event(self, event_type: str, timeout: float = 2.0) -> typing.Optional[EventEnvelope]:
        """等待某个事件发生。

        - 若事件已发生过（recent 记录），立即返回最新一条；
        - 否则订阅等待未来事件。
        """
        with self._lock:
            dq = self._recent.get(event_type)
            if dq:
                return dq[-1]

        holder = {}

        def _probe(env: EventEnvelope) -> None:
            holder["event"] = env

        sub = self.subscribe(_probe, {event_type})
        deadline = time.time() + timeout
        while time.time() < deadline:
            if "event" in holder:
                sub.unsubscribe()
                return holder["event"]
            time.sleep(0.01)
        sub.unsubscribe()
        return None

    # ------------------------------------------------------------------ #
    # 统计
    # ------------------------------------------------------------------ #
    @property
    def published_count(self) -> int:
        with self._lock:
            return self._published

    @property
    def current_size(self) -> int:
        return len(self._queue)

    @property
    def max_size(self) -> int:
        return self._queue.max_size

    def dropped_counts(self) -> typing.Dict[str, int]:
        with self._lock:
            return dict(self._dropped)

    def evicted_counts(self) -> typing.Dict[str, int]:
        with self._lock:
            return dict(self._evicted)

    def metrics(self) -> typing.Dict:
        with self._lock:
            return {
                "max_size": self._queue.max_size,
                "current_size": len(self._queue),
                "published": self._published,
                "dropped_total": sum(self._dropped.values()),
                "dropped_by_type": dict(self._dropped),
                "evicted_total": sum(self._evicted.values()),
                "evicted_by_type": dict(self._evicted),
                "subscribers": len(self._subscribers),
                "dispatch_async": self._dispatch_async,
            }

    def stop(self) -> None:
        self._running = False
        if self._dispatcher is not None:
            self._dispatcher.join(timeout=1.0)
