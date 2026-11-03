"""Explicit XIR inspection in an already prepared Vitis AI environment; no Runner."""
import argparse
import json
from pathlib import Path
from xmodel_metadata_core import inspect

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", type=Path, nargs="+")
    args = parser.parse_args()
    print(json.dumps({"scope": "OFFLINE_COMPILED_XIR_METADATA_ONLY",
                      "inference_executed": False, "device_accessed": False,
                      "models": [inspect(p) for p in args.models]}, indent=2))

if __name__ == "__main__":
    main()
