from pathlib import Path
import json
import re

path = Path(r"E:\项目\方案\aura_skill_package_plan_and_delivery_20261007.md")
content = path.read_text(encoding="utf-8")
links = re.findall(r"\[[^\]]*\]\(([^)]+)\)", content)
missing = []
local_count = 0
for target in links:
    target = target.strip("<>")
    if re.match(r"^[A-Za-z]:[/\\]", target):
        local_count += 1
        clean = re.sub(r":\d+$", "", target)
        if not Path(clean).is_file():
            missing.append(target)
inventory = json.loads((path.parents[1] / "tmp/aura_skill_review_20261007/project_inventory.json").read_text(encoding="utf-8"))
checks = {
    "all_local_links_exist": not missing,
    "even_code_fences": content.count("```") % 2 == 0,
    "inventory_count_matches": sum(inventory["counts_by_top_level"].values()) == 6277,
    "source_fingerprint_count_matches": len(inventory["source_fingerprints"]) == 20,
    "core_three_packages_named": all(name in content for name in ("command-guard-validation", "perception-freshness-benchmark", "async-result-validation")),
    "no_actual_packages_claimed": "本次尚未创建这些包" in content,
    "failed_validator_attempts_disclosed": "未实际完成用例执行" in content,
    "external_reuse_distinguished": "不是完整C包验证" in content,
    "budget_matches": 12 + 9 + 6 + 3 == 30 and 3 * 20 * 6 == 360,
}
report = {"file": str(path), "bytes": path.stat().st_size, "characters": len(content), "local_links": local_count, "missing_links": missing, "checks": checks}
(path.parents[1] / "tmp/aura_skill_review_20261007/plan_verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if all(checks.values()) else 1)
