"""Prove the exact allowed AST edits and unchanged publication boundaries."""
import ast
import copy
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def dump(node):
    return ast.dump(node, include_attributes=False)


def one(nodes, predicate):
    matches = [node for node in nodes if predicate(node)]
    assert len(matches) == 1
    return matches[0]


def assignment(module, name):
    return one(module.body, lambda node: isinstance(node, ast.Assign) and len(node.targets) == 1
               and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name)


def function(module, name):
    return one(module.body, lambda node: isinstance(node, ast.FunctionDef) and node.name == name)


def negation_if(loop):
    body = ast.parse("if True:\n    reasons.add('negation_missing')").body[0].body
    return one(loop.body, lambda node: isinstance(node, ast.If) and not node.orelse
               and [dump(item) for item in node.body] == [dump(item) for item in body])


def verify():
    manifest = json.loads((HERE / "SOURCE_MANIFEST.json").read_bytes())
    for relative, entry in manifest["sources"].items():
        assert hashlib.sha256((HERE / "before" / relative).read_bytes()).hexdigest() == entry["before_sha256"]
        assert hashlib.sha256((HERE / "after" / relative).read_bytes()).hexdigest() == entry["after_sha256"]
    name = "common/board_memory.py"
    old = ast.parse((HERE / "before" / name).read_bytes())
    prior = ast.parse((HERE / "intermediate" / name).read_bytes())
    new = ast.parse((HERE / "after" / name).read_bytes())
    old_neg, prior_neg, new_neg = [assignment(tree, "NEGATION") for tree in (old, prior, new)]
    assert new_neg.value.args[0].value == prior_neg.value.args[0].value + "|未喝"
    polarity = assignment(new, "POLAR_QUESTION")
    expected_polarity = ast.parse('POLAR_QUESTION = re.compile(r"(?<![不没])(?:去不去|买不买|做不做|要不要|能不能|会不会|是不是|有没有|可不可以)")').body[0]
    assert dump(polarity) == dump(expected_polarity)
    new.body.remove(polarity)
    new.body[new.body.index(new_neg)] = copy.deepcopy(old_neg)
    old_validator = function(old, "validate_compaction_text")
    new_validator = function(new, "validate_compaction_text")
    old_loop = one(old_validator.body, lambda node: isinstance(node, ast.For))
    new_loop = one(new_validator.body, lambda node: isinstance(node, ast.For))
    old_if, new_if = negation_if(old_loop), negation_if(new_loop)
    expected = ast.parse('''has_nonassertive_marker = (re.search(r"询问|提问|想知道|是否|能否|[?？]|无论|不管|不论", text) is not None
                          or POLAR_QUESTION.search(text) is not None)
source_negation_text = POLAR_QUESTION.sub(" ", source["text"]) if has_nonassertive_marker else source["text"]
summary_negation_text = POLAR_QUESTION.sub(" ", text)
if ((POLAR_QUESTION.search(source["text"]) and not has_nonassertive_marker)
        or ((meta.get("negated") is True or NEGATION.search(source_negation_text))
            and not NEGATION.search(summary_negation_text))):
    reasons.add("negation_missing")
''').body
    index = new_loop.body.index(new_if)
    assert [dump(node) for node in new_loop.body[index-3:index+1]] == [dump(node) for node in expected]
    assert [dump(node) for node in old_if.body] == [dump(node) for node in new_if.body]
    del new_loop.body[index-3:index]
    new_if.test = copy.deepcopy(old_if.test)
    assert dump(old_validator) == dump(new_validator)
    assert dump(old) == dump(new)

    name = "board/runtime/board_memory_policy.py"
    old = ast.parse((HERE / "before" / name).read_bytes())
    prior = ast.parse((HERE / "intermediate" / name).read_bytes())
    new = ast.parse((HERE / "after" / name).read_bytes())
    imported = one(new.body, lambda node: isinstance(node, ast.ImportFrom) and node.module == "common.board_memory")
    added_alias = one(imported.names, lambda node: node.name == "POLAR_QUESTION")
    assert added_alias.asname is None
    imported.names.remove(added_alias)
    prior_class = one(prior.body, lambda node: isinstance(node, ast.ClassDef) and node.name == "BoardSummaryClient")
    new_class = one(new.body, lambda node: isinstance(node, ast.ClassDef) and node.name == "BoardSummaryClient")
    assert dump(function(prior_class, "_messages")) == dump(function(new_class, "_messages"))
    prior_fragments = function(prior_class, "_fragments")
    new_fragments = function(new_class, "_fragments")
    prior_question = assignment(prior_fragments, "question_phrases")
    new_question = assignment(new_fragments, "question_phrases")
    expected_question = ast.parse("question_phrases = re.compile(r'(?=(' + POLAR_QUESTION.pattern + r'))')").body[0]
    assert dump(new_question) == dump(expected_question)
    new_fragments.body[new_fragments.body.index(new_question)] = copy.deepcopy(prior_question)
    assert dump(prior) == dump(new)
    old_class = one(old.body, lambda node: isinstance(node, ast.ClassDef) and node.name == "BoardSummaryClient")
    for node in (old_class, new_class):
        node.body = [item for item in node.body if getattr(item, "name", None) not in ("_messages", "_fragments")]
    assert dump(old) == dump(new)
    return dict(status="PASS", exact_fixed_question_and_condition_template=True,
                original_negation_if_body_identical=True, all_other_validator_nodes_identical=True,
                all_other_store_ast_identical=True, r1_prompt_ast_identical=True,
                r1_policy_only_polar_import_and_question_span_assignment_changed=True,
                other_actual_policy_ast_identical=True,
                schema_permissions_commit_cleanup_budget_cancel_ast_identical=True)


if __name__ == "__main__":
    report = verify()
    (HERE / "AST_BOUNDARY_PROOF.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report))
