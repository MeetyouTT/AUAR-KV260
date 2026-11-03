"""Read-only check for the actual selected-track motion feed."""
import json
import urllib.error
import urllib.request

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
result = {}
for name, path in (
    ("health", "/health"),
    ("motion_observation", "/v1/motion/observation"),
):
    request = urllib.request.Request("http://127.0.0.1:8790" + path)
    try:
        with opener.open(request, timeout=2) as response:
            payload = response.read(8193)
            item = {"http_status": response.status, "bytes": len(payload)}
            if len(payload) <= 8192 and name == "motion_observation":
                try:
                    value = json.loads(payload)
                    item.update(
                        protocol_version=value.get("protocol_version"),
                        source_kind=value.get("source_kind"),
                        state=value.get("state"),
                        source_frame_id=value.get("source_frame_id"),
                        source_mono_ms=value.get("source_mono_ms"),
                        has_target=isinstance(value.get("target"), dict),
                    )
                except (ValueError, AttributeError):
                    item["json"] = False
            result[name] = item
    except urllib.error.HTTPError as exc:
        result[name] = {"http_status": exc.code, "available": False}
    except Exception as exc:
        result[name] = {"error": type(exc).__name__}
print(json.dumps(result))
