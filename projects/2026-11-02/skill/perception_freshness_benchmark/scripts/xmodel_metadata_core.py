"""Read compiled XIR metadata only; no runner, device, inference or weight dump."""
import collections
import hashlib
import json
from pathlib import Path
import sys

import xir


def tensor_info(tensor):
    return {
        "name": tensor.name,
        "shape": list(tensor.dims),
        "dtype": str(tensor.dtype),
        "fix_point": tensor.get_attr("fix_point") if tensor.has_attr("fix_point") else None,
    }


def inspect(path):
    path = Path(path)
    graph = xir.Graph.deserialize(str(path))
    root = graph.get_root_subgraph()
    partitions = []
    children = list(root.toposort_child_subgraph()) or [root]
    for sub in children:
        ops = list(sub.get_ops())
        dtypes = collections.Counter()
        fixes = collections.Counter()
        constant_types = collections.Counter()
        for op in ops:
            t = op.get_output_tensor()
            dtypes[str(t.dtype)] += 1
            if t.has_attr("fix_point"):
                fixes[str(t.get_attr("fix_point"))] += 1
            if op.get_type().startswith("const"):
                constant_types[str(t.dtype)] += 1
        partitions.append({
            "name": sub.get_name(),
            "device": sub.get_attr("device") if sub.has_attr("device") else None,
            "fingerprint": hex(sub.get_attr("dpu_fingerprint")) if sub.has_attr("dpu_fingerprint") else None,
            "operation_counts": dict(sorted(collections.Counter(op.get_type() for op in ops).items())),
            "output_tensor_dtype_counts": dict(sorted(dtypes.items())),
            "constant_output_dtype_counts": dict(sorted(constant_types.items())),
            "fix_point_counts": dict(sorted(fixes.items())),
            "inputs": [tensor_info(t) for t in sub.get_input_tensors()],
            "outputs": [tensor_info(t) for t in sub.get_output_tensors()],
        })
    return {
        "filename": path.name,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "partitions": partitions,
        "dpu_partition_count": sum(s["device"] == "DPU" for s in partitions),
    }


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("Supply three read-only compiled model paths")
    print(json.dumps({"scope": "OFFLINE_COMPILED_XIR_METADATA_ONLY", "inference_executed": False,
                      "device_accessed": False, "models": [inspect(p) for p in sys.argv[1:]]}, indent=2))
