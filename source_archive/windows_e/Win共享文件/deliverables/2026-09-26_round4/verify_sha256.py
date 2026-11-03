# -*- coding: utf-8 -*-
"""按 MANIFEST_发送包.txt 逐份校验 SHA256（用法：python verify_sha256.py）。"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAN = os.path.join(HERE, "MANIFEST_发送包.txt")
ok = bad = miss = 0
lines = [l for l in open(MAN, encoding="utf-8").read().split("\n") if "SHA256" in l]
print("校验 %d 份文件（目录：%s）" % (len(lines), HERE))
for l in lines:
    name = l.split("SHA256")[0].strip().split("  ")[0].strip()
    want = l.split("SHA256")[-1].strip()
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        print("MISS  %s" % name)
        miss += 1
        continue
    got = hashlib.sha256(open(p, "rb").read()).hexdigest().upper()
    if got == want:
        print("OK    %s" % name)
        ok += 1
    else:
        print("FAIL  %s\n      期望 %s\n      实际 %s" % (name, want, got))
        bad += 1
print("\n结果：OK %d / FAIL %d / MISS %d" % (ok, bad, miss))
sys.exit(0 if (bad == 0 and miss == 0) else 1)
