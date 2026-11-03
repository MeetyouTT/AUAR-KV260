"""Create the two-source candidate from pinned originals without touching them."""
import ast
import difflib
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
STORE = "common/board_memory.py"
POLICY = "board/runtime/board_memory_policy.py"
PATHS = {
    STORE: REPAIR / "release_v20_identity_history_candidate/payload" / STORE,
    POLICY: REPAIR / "memory_observation_candidate_r2/after" / POLICY,
}
BEFORE = {
    STORE: "05095d249caf3598802d5951910b412affe167b508933c7e831e3ffacc4fc0d0",
    POLICY: "410e5b3eaf7986be6baa68d148469eb33443654ed0db597004518877732533c5",
}
PROMPT_PATH = REPAIR / "memory_negation_stability/prompt_candidate/after" / POLICY
PROMPT_SHA = "ef45290c89ec72fcbcaf0a0ceac7dd76816ea5f3e59099477fe77f5d38b52825"
ADDITIONS = ("未准备", "未能", "未校准", "未确认", "未购买", "未执行", "无法",
             "并非", "并未", "从未", "未曾", "不再")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def write_exact(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == raw
    else:
        path.write_bytes(raw)


def ast_differences(before, after, relative):
    old = ast.parse(before)
    new = ast.parse(after)
    if relative == STORE:
        old_node = next(node for node in old.body if isinstance(node, ast.Assign)
                        and any(isinstance(target, ast.Name) and target.id == "NEGATION" for target in node.targets))
        new_node = next(node for node in new.body if isinstance(node, ast.Assign)
                        and any(isinstance(target, ast.Name) and target.id == "NEGATION" for target in node.targets))
        old.body.remove(old_node)
        new.body.remove(new_node)
        names = ["NEGATION assignment"]
    else:
        old_class = next(node for node in old.body if isinstance(node, ast.ClassDef) and node.name == "BoardSummaryClient")
        new_class = next(node for node in new.body if isinstance(node, ast.ClassDef) and node.name == "BoardSummaryClient")
        names = [left.name for left, right in zip(old_class.body, new_class.body)
                 if isinstance(left, ast.FunctionDef) and ast.dump(left, include_attributes=False) != ast.dump(right, include_attributes=False)]
        assert names == ["_messages", "_fragments"]
        old_class.body = [node for node in old_class.body if getattr(node, "name", None) not in names]
        new_class.body = [node for node in new_class.body if getattr(node, "name", None) not in names]
    assert ast.dump(old, include_attributes=False) == ast.dump(new, include_attributes=False)
    return names


def main():
    originals = {name: path.read_bytes() for name, path in PATHS.items()}
    assert all(sha(originals[name]) == BEFORE[name] for name in originals)
    intermediate = PROMPT_PATH.read_bytes()
    assert sha(intermediate) == PROMPT_SHA
    store_text = originals[STORE].decode("utf-8")
    old_line = next(line for line in store_text.splitlines() if line.startswith("NEGATION = "))
    assert old_line.endswith('", re.I)')
    new_line = old_line[:-len('", re.I)')] + "|" + "|".join(ADDITIONS) + '", re.I)'
    store_after = store_text.replace(old_line, new_line).encode("utf-8")
    policy_text = intermediate.decode("utf-8")
    old_prompt = "                  '保留各条否定陈述的主语、对象和原否定表达。疑问句仍记为询问，保留原疑问形式。')"
    new_prompt = "                  '保留否定主客体、原表达及极性。双重否定不拆，疑问保留原形式，条件不作事实，先后状态不混淆。')"
    assert policy_text.count(old_prompt) == 1
    policy_text = policy_text.replace(old_prompt, new_prompt)
    old_begin = '        records = []\n        covered = 0\n        for index, source in enumerate(eligible):'
    new_begin = ("        question_phrases = re.compile(r'(?=(去不去|买不买|做不做|要不要|能不能|会不会|是不是|有没有|可不可以))')\n"
                 "        double_negations = re.compile(\n"
                 "            r'(?=((?:并不是|不是|并非|不能|不会|不得)[ \\t]{0,4}(?:' + NEGATION.pattern + r')))', re.I)\n"
                 "        records = []\n        covered = 0\n        for index, source in enumerate(eligible):")
    assert policy_text.count(old_begin) == 1
    policy_text = policy_text.replace(old_begin, new_begin)
    old_spans = "                     for match in pattern.finditer(text)]\n            for name in source['metadata'].get('names', []):"
    new_spans = ("                     for match in pattern.finditer(text)]\n"
                 "            # Overlapping expressions share one indivisible span, including\n"
                 "            # nested forms such as a question containing a double negation.\n"
                 "            spans.extend(match.span(1) for pattern in (question_phrases, double_negations)\n"
                 "                         for match in pattern.finditer(text))\n"
                 "            for name in source['metadata'].get('names', []):")
    assert policy_text.count(old_spans) == 1
    policy_text = policy_text.replace(old_spans, new_spans)
    changed = {STORE: store_after, POLICY: policy_text.encode("utf-8")}
    entries = {}
    for relative, raw in changed.items():
        names = ast_differences(originals[relative], raw, relative)
        ast.parse(raw, feature_version=(3, 9))
        write_exact(HERE / "before" / relative, originals[relative])
        write_exact(HERE / "after" / relative, raw)
        diff = "".join(difflib.unified_diff(originals[relative].decode().splitlines(keepends=True),
                                           raw.decode().splitlines(keepends=True),
                                           fromfile="before/" + relative, tofile="after/" + relative))
        write_exact(HERE / (relative.replace("/", "__") + ".diff"), diff.encode("utf-8"))
        entries[relative] = dict(before_sha256=BEFORE[relative], after_sha256=sha(raw), bytes=len(raw),
                                 local_source=str(HERE / "after" / relative), changed_ast=names,
                                 all_other_ast_identical=True)
    write_exact(HERE / "intermediate" / POLICY, intermediate)
    reverse_store = changed[STORE].decode().replace(new_line, old_line).encode()
    reverse_policy = changed[POLICY].decode().replace(new_prompt, old_prompt).replace(new_begin, old_begin).replace(new_spans, old_spans).encode()
    assert reverse_store == originals[STORE] and reverse_policy == intermediate
    proof = dict(store_reversed_exact_before=True, policy_reversed_exact_ef4529_intermediate=True,
                 prompt_intermediate_sha256=PROMPT_SHA, source_sha256=entries,
                 validator_function_unchanged=True, commit_schema_permissions_cleanup_budgets_cancel_unchanged=True)
    write_exact(HERE / "SOURCE_REVERSAL_PROOF.json", encoded(proof))
    write_exact(HERE / "SOURCE_MANIFEST.json", encoded(dict(
        status="TWO_SOURCE_OFFLINE_CANDIDATE", sources=entries,
        added_bounded_negation_forms=list(ADDITIONS), prompt_intermediate_sha256=PROMPT_SHA,
        product_sources=2, production_modified=False, private_database_or_model_accessed=False)))
    print(json.dumps(entries, ensure_ascii=True))


if __name__ == "__main__":
    main()
