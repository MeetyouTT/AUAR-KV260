#!/usr/bin/env python3
"""Build matching kernel dependencies and two ZOCL candidates; never install them."""
import argparse
import datetime
import difflib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

KERNEL_COMMIT = "19984dd147fa7fbb7cb14b17400263ad0925c189"
XRT_COMMIT = "43926231f7183688add2dccfd391b36a1f000bea"
EXPECTED_RELEASE = "5.15.36-xilinx-v2022.2"
CROSS = "/home/ghmd/Xilinx_2022.2/Vitis/2022.2/gnu/aarch64/lin/aarch64-linux/bin/aarch64-linux-gnu-"
JOBS = 8


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def config_values(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        if line.startswith("CONFIG_") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            values[line[2:-11]] = "n"
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "kernel", "baseline", "patched"])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.run_dir is None:
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        run = root / "evidence" / "build" / (stamp + "-" + args.phase)
        run.mkdir(parents=True, exist_ok=False)
        snapshot = run / "runner.py"
        shutil.copy2(__file__, snapshot)
        write_json(run / "runner.json", {"sha256": sha(snapshot), "source": str(Path(__file__).resolve())})
        return subprocess.call([sys.executable, str(snapshot), args.phase, "--root", str(root), "--run-dir", str(run)])

    run = args.run_dir.resolve()
    build = root / "build" / "kernel"
    source = root / "sources" / "linux-xlnx"
    original = root / "evidence" / "image_files" / "kernel.config"
    build.mkdir(parents=True, exist_ok=True)
    lock = (root / "build" / "build.lock").open("a+")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(("PETALINUX", "XILINX", "OECORE", "SDKTARGET")) or key in (
            "LD_LIBRARY_PATH", "LIBRARY_PATH", "CPATH", "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH",
            "KBUILD_OUTPUT", "KBUILD_EXTMOD", "KBUILD_EXTRA_SYMBOLS", "KBUILD_MODPOST_WARN", "KCFLAGS", "CFLAGS",
            "LDFLAGS", "LOCALVERSION", "MAKEFLAGS", "MFLAGS", "ARCH", "CROSS_COMPILE"):
            env.pop(key, None)
    env.update({"PATH": str(Path(CROSS).parent) + ":/usr/bin:/bin", "LC_ALL": "C", "ARCH": "arm64",
                "CROSS_COMPILE": CROSS, "KBUILD_BUILD_USER": "oe-user", "KBUILD_BUILD_HOST": "oe-host",
                "KBUILD_BUILD_VERSION": "1", "KBUILD_BUILD_TIMESTAMP": "Mon Oct 3 07:50:07 UTC 2022"})
    status = {"phase": args.phase, "jobs": JOBS, "cross_compile": CROSS,
              "original_config_sha256": sha(original), "commands": [], "passed": False}

    def command(name, argv, cwd=source):
        print("START {}: {}".format(name, " ".join(map(str, argv))), flush=True)
        start = time.monotonic()
        logfile = run / (name + ".log")
        with logfile.open("wb") as stream:
            result = subprocess.run(list(map(str, argv)), cwd=str(cwd), env=env, stdout=stream, stderr=subprocess.STDOUT)
        status["commands"].append({"name": name, "argv": list(map(str, argv)), "cwd": str(cwd),
                                   "log": str(logfile.relative_to(root)), "returncode": result.returncode,
                                   "elapsed_seconds": round(time.monotonic() - start, 3), "sha256": sha(logfile)})
        write_json(run / "status.json", status)
        print("END {}: exit={} log={}".format(name, result.returncode, logfile), flush=True)
        if result.returncode:
            print("\n".join(logfile.read_text(errors="replace").splitlines()[-18:]), flush=True)
            raise RuntimeError("{} failed with exit {}".format(name, result.returncode))
        return logfile

    def fixed_head(tree, expected):
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(tree), env=env, text=True).strip()
        if actual != expected:
            raise RuntimeError("Unexpected source commit: {} {}".format(tree, actual))
        return actual

    make = ["make", "-C", str(source), "O=" + str(build), "ARCH=arm64", "CROSS_COMPILE=" + CROSS]
    try:
        status["kernel_commit"] = fixed_head(source, KERNEL_COMMIT)
        command("compiler", [CROSS + "gcc", "--version"])
        command("assembler", [CROSS + "as", "--version"])
        command("linker", [CROSS + "ld", "--version"])
        if args.phase == "prepare":
            if (build / ".config").exists():
                raise RuntimeError("Refusing to overwrite an existing kernel configuration")
            shutil.copy2(original, build / ".config")
            # Original Honister kernel.bbclass::kernel_do_configure uses empty
            # .scmversion files in S and B; preserve CONFIG_LOCALVERSION_AUTO.
            for path in (source / ".scmversion", build / ".scmversion"):
                if path.exists() and path.read_bytes():
                    raise RuntimeError("Unexpected nonempty .scmversion")
                path.touch(exist_ok=True)
            command("olddefconfig", make + ["olddefconfig"])
            shutil.copy2(build / ".config", run / "resolved.config")
            a, b = config_values(original), config_values(build / ".config")
            changes = {key: {"original": a.get(key), "resolved": b.get(key)} for key in sorted(set(a) | set(b)) if a.get(key) != b.get(key)}
            write_json(run / "config-changes.json", changes)
            (run / "config.diff").write_text("".join(difflib.unified_diff(original.read_text().splitlines(True),
                (build / ".config").read_text().splitlines(True), fromfile="image/kernel.config", tofile="build/.config")))
            unexpected = set(changes) - {"CONFIG_CC_VERSION_TEXT"}
            if unexpected:
                raise RuntimeError("Kernel configuration changed; review required: " + ", ".join(sorted(unexpected)))
            command("modules-prepare", make + ["-j" + str(JOBS), "modules_prepare"])
            release = (command("kernelrelease", make + ["-s", "kernelrelease"]).read_text().splitlines())
            if EXPECTED_RELEASE not in release:
                raise RuntimeError("Kernel release mismatch: " + repr(release))
            write_json(build / "prepared.json", {"kernel_commit": KERNEL_COMMIT, "release": EXPECTED_RELEASE,
                "original_config_sha256": sha(original), "resolved_config_sha256": sha(build / ".config"),
                "config_changes": changes, "evidence": str(run.relative_to(root))})
        else:
            prepared = json.loads((build / "prepared.json").read_text())
            if prepared["resolved_config_sha256"] != sha(build / ".config"):
                raise RuntimeError("Prepared kernel configuration has changed")
            if args.phase == "kernel":
                command("kernel-symbols", make + ["-j" + str(JOBS), "vmlinux", "modules"])
                symvers = build / "Module.symvers"
                if not symvers.exists() or symvers.stat().st_size == 0:
                    raise RuntimeError("No complete Module.symvers produced")
                status["kernel_dependencies"] = {str(p.relative_to(root)): {"bytes": p.stat().st_size, "sha256": sha(p)}
                    for p in [build / "vmlinux", symvers, build / "System.map", build / ".config"]}
            else:
                symvers = build / "Module.symvers"
                if not symvers.exists() or symvers.stat().st_size == 0:
                    raise RuntimeError("Build kernel dependencies before the external module")
                tree = root / "sources" / ("XRT_baseline" if args.phase == "baseline" else "XRT_patched")
                status["xrt_commit"] = fixed_head(tree, XRT_COMMIT)
                command("source-diff-check", ["git", "diff", "--check"], cwd=tree)
                patch = command("source-diff", ["git", "diff", "--binary"], cwd=tree)
                if args.phase == "baseline" and patch.stat().st_size:
                    raise RuntimeError("Baseline source contains changes")
                module_dir = tree / "src" / "runtime_src" / "core" / "edge" / "drm" / "zocl"
                command("zocl-modules", make + ["-j" + str(JOBS), "M=" + str(module_dir), "modules"])
                artifacts = root / "artifacts" / args.phase
                artifacts.mkdir(parents=True, exist_ok=False)
                module = module_dir / "zocl.ko"
                shutil.copy2(module, artifacts / "zocl.debug.ko")
                shutil.copy2(module, artifacts / "zocl.ko")
                command("strip-debug", [CROSS + "strip", "--strip-debug", str(artifacts / "zocl.ko")])
                for filename in ("Module.symvers", "modules.order", "zocl.mod.c"):
                    shutil.copy2(module_dir / filename, artifacts / filename)
                command("modinfo", ["/sbin/modinfo", str(artifacts / "zocl.ko")])
                command("undefined-symbols", [CROSS + "nm", "-u", str(artifacts / "zocl.ko")])
                command("elf-sections", [CROSS + "readelf", "-h", "-S", str(artifacts / "zocl.ko")])
                status["artifacts"] = {str(p.relative_to(root)): {"bytes": p.stat().st_size, "sha256": sha(p)}
                    for p in sorted(artifacts.iterdir()) if p.is_file()}
                status["kernel_symvers_sha256"] = sha(symvers)
        status["passed"] = True
        print("PHASE PASSED: {}".format(args.phase), flush=True)
    except Exception as error:
        status["error"] = str(error)
        print("PHASE FAILED: {}".format(error), flush=True)
        return 1
    finally:
        write_json(run / "status.json", status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
