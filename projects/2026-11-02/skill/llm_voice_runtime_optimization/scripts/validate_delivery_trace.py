"""Audit normalized delivery/ACK/source decisions; never opens production databases."""
import argparse
import json
import math
from pathlib import Path

def finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
def digest(x):
    return isinstance(x, str) and len(x) == 64 and all(c in "0123456789abcdef" for c in x.lower())

def audit(data):
    errors, unknown = [], []
    requests, current, sources, summaries = {}, {}, {}, {}
    accepted_acks = 0
    previous_time = None
    if data.get("schema") != "aura.delivery_source_trace.v1":
        unknown.append("unsupported or missing schema")
    events = data.get("events", [])
    if not isinstance(events, list) or not events:
        return {"status": "UNKNOWN", "errors": [], "unknown": ["missing events"]}
    for index, event in enumerate(events):
        prefix = "event[%d]" % index
        if not isinstance(event, dict):
            errors.append(prefix + " is not an object")
            continue
        now = event.get("time_ms")
        if not finite(now) or now < 0:
            errors.append(prefix + " invalid time_ms")
            continue
        if previous_time is not None and now < previous_time:
            errors.append(prefix + " time moved backwards")
        previous_time = now
        scope, kind = event.get("scope"), event.get("kind")
        if not scope:
            unknown.append(prefix + " missing scope")
            continue
        rid = event.get("request_id")
        if kind == "request":
            if not rid or rid in requests:
                errors.append(prefix + " missing or duplicate request")
                continue
            required = ["generation", "deadline_ms", "expected_sha256", "expected_samples", "expected_segments"]
            if any(k not in event for k in required):
                unknown.append(prefix + " incomplete request contract")
                continue
            if (type(event["generation"]) is not int or event["generation"] < 0 or
                not finite(event["deadline_ms"]) or event["deadline_ms"] < now or
                not digest(event["expected_sha256"]) or
                type(event["expected_samples"]) is not int or event["expected_samples"] <= 0 or
                type(event["expected_segments"]) is not int or event["expected_segments"] <= 0):
                errors.append(prefix + " invalid request contract")
                continue
            dependencies = event.get("source_dependencies")
            if not isinstance(dependencies, list):
                unknown.append(prefix + " input source provenance is not declared")
                dependencies = []
            elif any(not isinstance(ref, dict) or not ref.get("source_id") or
                     type(ref.get("version")) is not int for ref in dependencies):
                errors.append(prefix + " invalid source dependency contract")
                continue
            requests[rid] = dict(event, cancelled=False, ack=False, chunks=set(), dependencies=dependencies)
            current[scope] = rid
            continue
        if kind == "source_invalidate":
            key = (scope, event.get("source_id"))
            if key not in sources:
                unknown.append(prefix + " invalidation source absent")
            else:
                sources[key]["valid"] = False
                sources[key]["version"] += 1
            continue
        if kind == "summary_commit":
            refs = event.get("sources")
            valid = bool(refs) and event.get("validated") is True
            if not isinstance(refs, list):
                valid = False
                refs = []
            for ref in refs:
                source = sources.get((scope, ref.get("source_id")))
                valid = valid and source is not None and source["valid"] and source["version"] == ref.get("version")
            if event.get("accepted") is True:
                if not valid or not event.get("summary_id"):
                    errors.append(prefix + " accepted stale/unvalidated summary")
                else:
                    summaries[(scope, event["summary_id"])] = refs
            elif type(event.get("accepted")) is not bool:
                unknown.append(prefix + " missing summary decision")
            continue
        if kind == "raw_delete":
            refs = summaries.get((scope, event.get("summary_id")), [])
            source_id = event.get("source_id")
            valid = any(ref.get("source_id") == source_id and
                        sources.get((scope, source_id), {}).get("valid") and
                        sources[(scope, source_id)]["version"] == ref.get("version") for ref in refs)
            if not valid:
                errors.append(prefix + " raw deletion without a validated matching committed summary")
            continue
        request = requests.get(rid)
        if request is None:
            unknown.append(prefix + " request context absent")
            continue
        fresh = (scope == request["scope"] and current.get(scope) == rid and
                 event.get("generation") == request["generation"] and
                 not request["cancelled"] and now <= request["deadline_ms"])
        for ref in request["dependencies"]:
            source = sources.get((request["scope"], ref["source_id"]))
            fresh = fresh and source is not None and source["valid"] and source["version"] == ref["version"]
        if kind == "cancel":
            if scope != request["scope"]:
                errors.append(prefix + " cancellation scope mismatch")
            else:
                request["cancelled"] = True
            continue
        if kind in ("chunk_decision", "ack_decision"):
            accepted = event.get("accepted")
            if type(accepted) is not bool:
                unknown.append(prefix + " missing delivery decision")
                continue
            if not accepted:
                continue
            if not fresh:
                errors.append(prefix + " accepted stale/cancelled/cross-scope delivery")
                continue
            if kind == "chunk_decision":
                segment = event.get("segment_index")
                if type(segment) is not int or segment != len(request["chunks"]):
                    errors.append(prefix + " accepted repeated/missing/out-of-order segment")
                elif segment >= request["expected_segments"]:
                    errors.append(prefix + " accepted unexpected segment")
                else:
                    request["chunks"].add(segment)
            else:
                if request["ack"]:
                    errors.append(prefix + " accepted duplicate complete ACK")
                elif (event.get("sha256") != request["expected_sha256"] or
                      event.get("samples") != request["expected_samples"] or
                      len(request["chunks"]) != request["expected_segments"]):
                    errors.append(prefix + " accepted incomplete or mismatched complete ACK")
                else:
                    request["ack"] = True
                    accepted_acks += 1
        elif kind == "memory_commit":
            accepted = event.get("accepted")
            if accepted is not True:
                if type(accepted) is not bool:
                    unknown.append(prefix + " missing memory decision")
                continue
            valid = fresh and event.get("role") in ("user", "assistant")
            if event.get("role") == "assistant":
                valid = valid and request["ack"]
            if not valid:
                errors.append(prefix + " memory commit lacks current scope/valid playback")
                continue
            source_id = event.get("source_id")
            version = event.get("source_version")
            key = (scope, source_id)
            if not source_id or type(version) is not int or version < 1 or key in sources:
                errors.append(prefix + " invalid or reused source identity")
            else:
                sources[key] = {"version": version, "valid": True}
        elif kind == "memory_read":
            if event.get("accepted") is True and (not fresh or event.get("authorized") is not True):
                errors.append(prefix + " unauthorized or cross-scope memory read")
            elif type(event.get("accepted")) is not bool:
                unknown.append(prefix + " missing memory read decision")
        else:
            unknown.append(prefix + " unsupported event kind")
    if accepted_acks == 0:
        unknown.append("no accepted positive complete ACK")
    return {"status": "FAIL" if errors else ("UNKNOWN" if unknown else "PASS"),
            "scope": "normalized_saved_decisions_only", "evidence_kind": data.get("evidence_kind", "UNKNOWN"),
            "errors": errors, "unknown": unknown, "accepted_complete_acks": accepted_acks,
            "memory_sources": len(sources), "validated_summaries": len(summaries),
            "private_database_opened": False, "model_invoked": False,
            "actual_semantic_recall_verified": False, "physical_playback_verified": False}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        result = audit(json.loads(args.input.read_text(encoding="utf-8-sig")))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"status": "UNKNOWN", "errors": [], "unknown": [str(exc)]}
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return {"PASS": 0, "FAIL": 1, "UNKNOWN": 2}[result["status"]]

if __name__ == "__main__":
    raise SystemExit(main())
