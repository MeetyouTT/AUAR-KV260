# -*- coding: utf-8 -*-
"""三层 Validator 单测：正例 + 反例（伪造事实/过期/越权/白名单）。"""
import pytest

from board.runtime.validator import ValidationChain, ValidationContext


def make_scene(seq=125, valid_until=200000, people=1, pos="left", track=7):
    return {
        "schema_version": "1.0",
        "scene_seq": seq,
        "captured_at_ms": 1000,
        "valid_until_ms": valid_until,
        "camera_state": "online",
        "people_count": people,
        "current_target": {"track_id": track, "position": pos,
                           "confidence": 0.91, "source_frame_id": 888},
        "recent_events": [{"type": "person_enter", "track_id": track, "age_ms": 500}],
        "uncertainty": [],
    }


def make_response(request_id="req-1", scene_seq_used=125,
                  reply="我看到画面左侧有一位来访者。",
                  emotion="friendly", avatar="wave", claims=None, **kw):
    resp = {
        "protocol_version": "1.0",
        "request_id": request_id,
        "scene_seq_used": scene_seq_used,
        "reply_text": reply,
        "emotion": emotion,
        "avatar_action": avatar,
        "visual_claims": claims if claims is not None
        else [{"fact": "person_on_left", "source_track_id": 7}],
    }
    resp.update(kw)
    return resp


@pytest.fixture
def chain():
    return ValidationChain()


def base_ctx(**kw):
    ctx = ValidationContext(
        request_id="req-1",
        scene_state=make_scene(),
        scene_seq=125,
        allowed_emotions=("neutral", "friendly", "curious"),
        allowed_avatar_actions=("idle", "wave", "nod"),
        now_ms=5000,
        max_reply_len=200,
    )
    for k, v in kw.items():
        setattr(ctx, k, v)
    return ctx


def test_valid_response_passes(chain):
    res = chain.validate_response(make_response(), base_ctx())
    assert res.ok, res.to_dict()


def test_schema_missing_required(chain):
    res = chain.validate_response({"protocol_version": "1.0"}, base_ctx())
    assert not res.ok
    assert res.layer == "schema.response"


def test_schema_rejects_control_requests(chain):
    # schema 层：control_requests 非空数组违反 maxItems=0
    res = chain.validate_response(make_response(control_requests=[{"do": "overlay"}]), base_ctx())
    assert not res.ok


def test_request_id_mismatch(chain):
    res = chain.validate_response(make_response(request_id="req-old"), base_ctx())
    assert not res.ok
    assert any(i.code == "semantic.request_id_mismatch" for i in res.issues)


def test_scene_seq_ahead(chain):
    res = chain.validate_response(make_response(scene_seq_used=999), base_ctx())
    assert not res.ok
    assert any(i.code == "semantic.scene_seq_ahead" for i in res.issues)


def test_scene_expired(chain):
    res = chain.validate_response(make_response(), base_ctx(now_ms=300000))
    assert not res.ok
    assert any(i.code == "semantic.scene_expired" for i in res.issues)


def test_visual_claim_ungrounded(chain):
    # LLM 伪造"右边有人"，但场景只有左边 → 拒绝
    resp = make_response(claims=[{"fact": "person_on_right", "source_track_id": 7}])
    res = chain.validate_response(resp, base_ctx())
    assert not res.ok
    assert any(i.code == "policy.visual_claim_ungrounded" for i in res.issues)


def test_unknown_fact_rejected(chain):
    resp = make_response(claims=[{"fact": "dragon_flying"}])
    res = chain.validate_response(resp, base_ctx())
    assert not res.ok
    assert any(i.code == "policy.unknown_fact" for i in res.issues)


def test_emotion_not_allowed(chain):
    res = chain.validate_response(make_response(emotion="angry"), base_ctx())
    assert not res.ok
    assert any(i.code == "policy.emotion_not_allowed" for i in res.issues)


def test_avatar_not_allowed(chain):
    res = chain.validate_response(make_response(avatar="dance"), base_ctx())
    assert not res.ok
    assert any(i.code == "policy.avatar_not_allowed" for i in res.issues)


def test_reply_too_long(chain):
    res = chain.validate_response(make_response(reply="很" * 300), base_ctx())
    assert not res.ok
    assert any(i.code == "policy.reply_too_long" for i in res.issues)


def test_track_not_found(chain):
    resp = make_response(claims=[{"fact": "person_present", "source_track_id": 999}])
    res = chain.validate_response(resp, base_ctx())
    assert not res.ok
    assert any(i.code == "semantic.track_not_found" for i in res.issues)


def test_no_person_requires_uncertain_reply(chain):
    # 无人场景：no_person 事实允许
    resp = make_response(reply="不确定，当前没有看到人。",
                         claims=[{"fact": "no_person"}])
    ctx = base_ctx(scene_state=make_scene(people=0, pos=None, track=None))
    res = chain.validate_response(resp, ctx)
    assert res.ok, res.to_dict()


def test_validate_scene_state_expired(chain):
    ctx = base_ctx(now_ms=999999)
    res = chain.validate_scene_state(make_scene(valid_until=100), ctx)
    assert not res.ok
