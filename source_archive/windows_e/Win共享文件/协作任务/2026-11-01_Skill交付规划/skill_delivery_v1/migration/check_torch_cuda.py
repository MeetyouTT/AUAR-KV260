"""Optional explicit CUDA smoke probe; no model loading. Default is package metadata only."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
from datetime import datetime, timezone

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--platform-id", required=True)
    p.add_argument("--probe-cuda", action="store_true",
                   help="Explicitly execute a tiny 8x8 CUDA matrix multiplication.")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("refusing to overwrite an existing receipt")
    result = {"schema": "aura.torch_probe.v1", "platform_id": args.platform_id,
              "recorded_utc": datetime.now(timezone.utc).isoformat(),
              "os": platform.system(), "python_version": platform.python_version(),
              "python_executable": sys.executable, "cuda_probe_requested": args.probe_cuda,
              "model_loaded": False, "cuda_smoke_pass": None, "status": "METADATA_ONLY"}
    for name in ("torch", "torchaudio", "onnxruntime", "sherpa-onnx"):
        try:
            result[name + "_installed_version"] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name + "_installed_version"] = None
    if args.probe_cuda:
        try:
            import torch
            result["torch_cuda_build"] = torch.version.cuda
            result["cuda_available"] = bool(torch.cuda.is_available())
            if not result["cuda_available"]:
                raise RuntimeError("CUDA unavailable; no CPU fallback is accepted")
            result["gpu_name"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            result["gpu_memory_total_bytes"] = int(props.total_memory)
            result["compute_capability"] = list(torch.cuda.get_device_capability(0))
            x = torch.ones((8, 8), device="cuda")
            y = x @ x
            torch.cuda.synchronize()
            if not bool(torch.all(y == 8).item()):
                raise RuntimeError("CUDA arithmetic check failed")
            result["cuda_smoke_pass"] = True
            result["status"] = "CUDA_SMOKE_PASS_NOT_MODEL_ACCEPTANCE"
        except Exception as exc:
            result["cuda_smoke_pass"] = False
            result["status"] = "FAIL"
            result["error_type"] = type(exc).__name__
            result["error"] = str(exc)[:1200]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "FAIL" else 0

if __name__ == "__main__":
    raise SystemExit(main())
