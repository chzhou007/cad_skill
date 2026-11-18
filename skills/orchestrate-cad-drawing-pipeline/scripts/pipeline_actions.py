"""Bounded, read-only capability and project-state queries; never imports pipeline.

Discovery reads Python AST and the explicit feature ledger. It does not execute
handlers, infer arguments from command names, or choose an authority by mtime.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import sys


DEFAULT_LIMIT = 10
MAX_LIMIT = 50
UNKNOWN = "unknown"
OWNER = "orchestrate-cad-drawing-pipeline"
DEFAULT_PIPELINE = Path(__file__).with_name("pipeline.py")
DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "assets/feature-registry.json"
DEFAULT_OVERRIDES = Path(__file__).resolve().parents[1] / "assets/pipeline-action-overrides.json"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(path):
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object: " + str(path))
    return value


def _ref(path, **extra):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=sha256(path), **extra)


def _bounds(limit, offset=0):
    if type(limit) is not int or not 1 <= limit <= MAX_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
    if type(offset) is not int or offset < 0:
        raise ValueError("offset must be a nonnegative integer")


def _page(items, limit=DEFAULT_LIMIT, offset=0):
    _bounds(limit, offset)
    return dict(total=len(items), returned=len(items[offset:offset + limit]),
                offset=offset, limit=limit, truncated=offset + limit < len(items),
                items=items[offset:offset + limit])


def _compact(value, limit=DEFAULT_LIMIT, depth=3):
    """Bound nested untrusted metadata as well as the outer result count."""
    if isinstance(value, str):
        return value if len(value) <= 600 else value[:600] + "… [truncated]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if depth <= 0:
        return {"detail_type": type(value).__name__, "count": len(value)}
    if isinstance(value, list):
        return dict(total=len(value), items=[_compact(x, limit, depth - 1) for x in value[:limit]],
                    truncated=len(value) > limit)
    if isinstance(value, dict):
        result = {str(k): _compact(v, limit, depth - 1) for k, v in list(value.items())[:limit]}
        if len(value) > limit:
            result["_truncated_fields"] = len(value) - limit
        return result
    return UNKNOWN


def _expr(node):
    return ast.unparse(node)


def _literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return {"source_expression": _expr(node)}


def _command_operand(node):
    return (_expr(node) == "sys.argv[1]" or
            isinstance(node, ast.Attribute) and node.attr == "command")


def _commands(test):
    """Only explicit command comparison literals; startswith is not a command."""
    found = []
    for node in ast.walk(test):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1:
            continue
        if _command_operand(node.left):
            value = _literal(node.comparators[0])
            if isinstance(node.ops[0], ast.Eq) and isinstance(value, str):
                found.append(value)
            elif isinstance(node.ops[0], ast.In) and isinstance(value, (tuple, list)):
                found.extend(x for x in value if isinstance(x, str))
    return list(dict.fromkeys(found))


class _NotStatic(Exception):
    pass


def _evaluate(node, command, variables):
    """A small safe expression evaluator, never eval/exec or module imports.

    It evaluates actual dispatch conditions (including source-coded 'viewer'
    branches) rather than inventing routing from the spelling of a command.
    """
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id in variables:
        return variables[node.id]
    if _expr(node) == "sys.argv[1]":
        return command
    if isinstance(node, (ast.Tuple, ast.List)):
        return [_evaluate(x, command, variables) for x in node.elts]
    if isinstance(node, ast.IfExp):
        return _evaluate(node.body if _evaluate(node.test, command, variables) else node.orelse,
                         command, variables)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _evaluate(node.left, command, variables) + _evaluate(node.right, command, variables)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _evaluate(node.operand, command, variables)
    if isinstance(node, ast.BoolOp):
        values = [_evaluate(x, command, variables) for x in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        left = _evaluate(node.left, command, variables)
        right = _evaluate(node.comparators[0], command, variables)
        op = node.ops[0]
        if isinstance(op, ast.Eq):
            return left == right
        if isinstance(op, ast.NotEq):
            return left != right
        if isinstance(op, ast.In):
            return left in right
        if isinstance(op, ast.NotIn):
            return left not in right
    raise _NotStatic()


def _selected_nodes(statements, command, variables=None):
    variables = dict(variables or {})
    for statement in statements:
        yield statement
        if isinstance(statement, ast.Assign):
            try:
                value = _evaluate(statement.value, command, variables)
                for target in statement.targets:
                    if isinstance(target, ast.Name):
                        variables[target.id] = value
            except _NotStatic:
                pass
        elif isinstance(statement, ast.If):
            try:
                branch = statement.body if _evaluate(statement.test, command, variables) else statement.orelse
            except _NotStatic:
                branch = statement.body + statement.orelse
            yield from _selected_nodes(branch, command, variables)
        elif isinstance(statement, (ast.Try, ast.With)):
            yield from _selected_nodes(statement.body, command, variables)
        elif isinstance(statement, ast.For):
            try:
                values = _evaluate(statement.iter, command, variables)
            except _NotStatic:
                values = []
            if isinstance(statement.target, ast.Name) and isinstance(values, (list, tuple)):
                for value in values:
                    yield from _selected_nodes(statement.body, command, dict(variables, **{statement.target.id: value}))


def _argument(call, variables=None):
    flags = []
    for arg in call.args:
        try:
            value = _evaluate(arg, "", variables or {})
        except _NotStatic:
            return {"source_expression": _expr(call), "status": "requires_owner_help"}
        if isinstance(value, str):
            flags.append(value)
    result = {"flags": flags}
    for kw in call.keywords:
        if kw.arg in ("required", "default", "choices", "nargs", "action", "type", "dest", "help"):
            result[kw.arg] = _literal(kw.value)
    return result


def _script_arguments(path):
    """Static observations only. Dynamic/group constraints remain owner-owned."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8-sig"))
    rows = []

    def walk(statements, variables=None):
        variables = variables or {}
        for node in statements:
            if isinstance(node, ast.For):
                try:
                    values = _evaluate(node.iter, "", variables)
                except _NotStatic:
                    values = []
                if isinstance(node.target, ast.Name) and isinstance(values, (list, tuple)):
                    for value in values:
                        walk(node.body, dict(variables, **{node.target.id: value}))
            else:
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    call = node.value
                    if isinstance(call.func, ast.Attribute) and call.func.attr == "add_argument":
                        rows.append(_argument(call, variables))
                for field in ("body", "orelse", "finalbody"):
                    body = getattr(node, field, None)
                    if isinstance(body, list):
                        walk(body, variables)

    walk(tree.body)
    return rows


def _script_index(skill_root):
    result = {}
    for path in skill_root.glob("*/scripts/*.py"):
        result.setdefault(path.stem, []).append(path.resolve())
    return result


def _implementation(nodes, index, skill_root, pipeline):
    imports = []
    for node in nodes:
        if isinstance(node, ast.ImportFrom) and node.module:
            paths = index.get(node.module.rsplit(".", 1)[-1], [])
            if not paths:
                continue
            for path in paths:
                imports.append(dict(module=node.module, script=str(path),
                                    relative_script=path.relative_to(skill_root).as_posix(),
                                    owner=path.relative_to(skill_root).parts[0],
                                    imported_symbols=[a.name for a in node.names],
                                    resolution="unique_local_module" if len(paths) == 1 else "ambiguous_local_module"))
    seen = set()
    result = []
    for row in imports:
        key = (row["module"], row["script"])
        if key not in seen:
            result.append(row)
            seen.add(key)
    if not result:
        result.append(dict(module="pipeline", script=str(pipeline),
                           relative_script=pipeline.relative_to(skill_root).as_posix(),
                           owner=OWNER, imported_symbols=[], resolution="local_handler"))
    return result


def discover(pipeline=DEFAULT_PIPELINE, feature_registry=DEFAULT_REGISTRY, overrides=DEFAULT_OVERRIDES):
    """Return complete in-memory registry; callers must use query() for output."""
    pipeline, feature_registry = Path(pipeline).resolve(), Path(feature_registry).resolve()
    tree = ast.parse(pipeline.read_text(encoding="utf-8-sig"))
    functions = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if "_main" not in functions or "main" not in functions:
        raise ValueError("Expected _main and main dispatchers in " + str(pipeline))
    skill_root = pipeline.parents[2]
    index = _script_index(skill_root)
    features = _json(feature_registry).get("features", [])
    if not isinstance(features, list):
        raise ValueError("feature registry features must be an array")
    entries = {}
    current = None
    for node in functions["_main"].body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "add_parser" and call.args:
                name = _literal(call.args[0])
                if isinstance(name, str):
                    current = dict(command=name, discovery="argparse", source_line=node.lineno,
                                   handler=None, arguments=[], implementations=[], notes=[])
                    entries[name] = current
        elif current and isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "add_argument":
                current["arguments"].append(_argument(call))
    for node in ast.walk(functions["_main"]):
        if not isinstance(node, ast.If):
            continue
        for command in _commands(node.test):
            if command not in entries:
                continue
            body = ast.Module(body=node.body, type_ignores=[])
            handlers = [n.func.id for n in ast.walk(body) if isinstance(n, ast.Call)
                        and isinstance(n.func, ast.Name) and n.func.id in functions]
            if handlers:
                entries[command]["handler"] = handlers[0]
    # The parser's final else explicitly dispatches validate(args.run).
    if "validate" in entries and entries["validate"]["handler"] is None:
        for node in ast.walk(functions["_main"]):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "validate":
                entries["validate"]["handler"] = "validate"
    for row in entries.values():
        handler = functions.get(row["handler"])
        row["implementations"] = _implementation(list(_selected_nodes(handler.body, row["command"])) if handler else [],
                                                 index, skill_root, pipeline)
        row["argument_contract"] = "pipeline_argparse"
    for node in functions["main"].body:
        if not isinstance(node, ast.If):
            continue
        commands = _commands(node.test)
        # Do not count runtime wrapping of _main as a manual command route.
        if not any(isinstance(n, ast.ImportFrom) and any(a.name == "main" for a in n.names)
                   for n in ast.walk(ast.Module(body=node.body, type_ignores=[]))):
            continue
        for command in commands:
            selected = [n for n in _selected_nodes(node.body, command)
                        if not isinstance(n, ast.ImportFrom) or any(a.name == "main" for a in n.names)]
            implementations = _implementation(selected, index, skill_root, pipeline)
            row = dict(command=command, discovery="manual_dispatch", source_line=node.lineno,
                       handler="main", arguments=[], implementations=implementations,
                       argument_contract="delegated_to_owner", notes=["Not listed by legacy pipeline argparse help; parameters belong to the delegated entry point."])
            entries[command] = row
    explicit = _json(overrides) if overrides and Path(overrides).is_file() else {}
    for command, update in explicit.get("commands", {}).items():
        if command not in entries:
            raise ValueError("Override references an undiscovered command: " + command)
        for key in ("description", "notes", "stage", "related_scripts"):
            if key in update:
                entries[command][key] = update[key]
    for row in entries.values():
        scripts = {x["relative_script"] for x in row["implementations"]}
        # Generic pipeline.py membership is not evidence for every capability.
        scripts.discard(pipeline.relative_to(skill_root).as_posix())
        row["feature_ids"] = sorted(f["id"] for f in features if isinstance(f, dict)
                                    and scripts.intersection(f.get("files", [])))
        row["owners"] = sorted({x["owner"] for x in row["implementations"]})
        row["feature_relation"] = "exact_implementation_file_membership" if row["feature_ids"] else "unknown_no_exact_file_link"
    return dict(schema_version=1, status="source_discovered_not_execution_or_acceptance",
                sources={"pipeline": _ref(pipeline), "feature_registry": _ref(feature_registry),
                         "overrides": _ref(overrides) if overrides and Path(overrides).is_file() else None},
                counts=dict(commands=len(entries), argparse=sum(x["discovery"] == "argparse" for x in entries.values()),
                            manual_dispatch=sum(x["discovery"] == "manual_dispatch" for x in entries.values()),
                            features=len(features)),
                entries=sorted(entries.values(), key=lambda row: row["command"]), features=features)


def _brief(row, limit):
    return dict(command=row["command"], discovery=row["discovery"], owners=row["owners"],
                modules=[x["module"] for x in row["implementations"]][:limit],
                feature_ids=row["feature_ids"][:limit], feature_count=len(row["feature_ids"]),
                description=row.get("description", UNKNOWN), source_line=row["source_line"])


def query(registry, operation="list", value=None, limit=DEFAULT_LIMIT, offset=0):
    _bounds(limit, offset)
    result = {key: registry[key] for key in ("schema_version", "status", "sources", "counts")}
    result["operation"] = operation
    rows = registry["entries"]
    if operation == "list":
        result["results"] = _page([_brief(x, limit) for x in rows], limit, offset)
    elif operation == "search":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("search requires nonempty text")
        needle = value.casefold()
        feature_hits = {f["id"] for f in registry["features"] if needle in json.dumps(f, ensure_ascii=False).casefold()}
        matches = [r for r in rows if needle in json.dumps(r, ensure_ascii=False).casefold()
                   or feature_hits.intersection(r["feature_ids"])]
        matches.sort(key=lambda r: (r["command"].casefold() != needle, r["command"]))
        result["query"] = value
        result["results"] = _page([_brief(x, limit) for x in matches], limit, offset)
    elif operation == "explain":
        row = next((r for r in rows if r["command"] == value), None)
        if row is None:
            raise ValueError("Unknown command: " + str(value))
        detail = {k: row[k] for k in ("command", "discovery", "source_line", "handler", "argument_contract", "feature_relation", "owners")}
        detail["description"] = row.get("description", UNKNOWN)
        detail["stage"] = row.get("stage", UNKNOWN)
        detail["notes"] = _compact(row["notes"], limit)
        detail["related_scripts"] = _compact(row.get("related_scripts", []), limit)
        detail["feature_ids"] = _page(row["feature_ids"], limit, offset)
        implementations = []
        for impl in row["implementations"]:
            item = dict(impl, source=_ref(impl["script"]))
            if row["argument_contract"] == "delegated_to_owner":
                item["observed_arguments"] = _page(_script_arguments(impl["script"]), limit, offset)
                item["argument_note"] = "Static observations only; inspect owner --help for groups, modes, and dynamic requirements."
            implementations.append(item)
        detail["implementations"] = _page(implementations, limit, offset)
        detail["arguments"] = _page(row["arguments"], limit, offset)
        detail["help_argv"] = [sys.executable, registry["sources"]["pipeline"]["path"], value, "--help"]
        result["result"] = detail
    elif operation == "feature":
        feature = next((f for f in registry["features"] if f.get("id") == value), None)
        if feature is None:
            raise ValueError("Unknown feature ID: " + str(value))
        result["feature"] = {k: _compact(feature.get(k, UNKNOWN), limit) for k in
                             ("id", "description", "families", "acceptance_status", "depends_on")}
        for key in ("files", "tests", "evidence_references"):
            result["feature"][key] = _page(feature.get(key, []), limit, offset)
        result["feature"]["detail_pointer"] = "/features/" + str(registry["features"].index(feature))
        result["results"] = _page([_brief(r, limit) for r in rows if value in r["feature_ids"]], limit, offset)
    else:
        raise ValueError("Unknown operation: " + str(operation))
    return result


def current_project(authority=None, expected_sha256=None, pointer=None, limit=DEFAULT_LIMIT):
    _bounds(limit)
    pointer_ref = None
    project_id = UNKNOWN
    if pointer:
        if authority or expected_sha256:
            raise ValueError("Use either pointer or authority plus sha256, not both")
        pointer = Path(pointer).resolve()
        data = _json(pointer)
        target = data.get("authority")
        if not isinstance(target, dict) or not isinstance(target.get("path"), str):
            raise ValueError("Pointer requires authority.path and authority.sha256")
        authority = (pointer.parent / target["path"]).resolve()
        expected_sha256 = target.get("sha256")
        project_id = data.get("project_id", UNKNOWN)
        pointer_ref = _ref(pointer)
    if not authority:
        raise ValueError("Explicit --authority PATH --sha256 HASH or --pointer PATH required; no latest-file search is performed")
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        raise ValueError("A 64-character expected authority sha256 is required")
    authority = Path(authority).resolve()
    actual = sha256(authority)
    if actual.lower() != expected_sha256.lower():
        raise ValueError("Authority SHA-256 mismatch: " + str(authority))
    data = _json(authority)
    if project_id != UNKNOWN and data.get("project_id", project_id) != project_id:
        raise ValueError("Pointer and authority project_id differ")
    semantic = {key: _compact(data.get(key, UNKNOWN), limit) for key in
                ("status", "current_metrics", "review", "full_fixed_input_delivery_complete",
                 "whole_goal_complete", "local_topologies", "crossview_and_fusion")}
    for key in ("compact_state", "semantic_state"):
        if key in data:
            semantic[key] = _compact(data[key], limit)
    unresolved = data.get("unresolved_classes", data.get("remaining_work", UNKNOWN))
    return dict(schema_version=1, status="hash_verified_authority_read_only",
                project_id=data.get("project_id", project_id), authority=_ref(authority),
                pointer=pointer_ref, semantic_state=semantic,
                unresolved_classes=_compact(unresolved, limit),
                evidence_boundary="Only explicitly recorded state is reported; authority hash is checked, referenced artifacts are not replayed. This query does not establish topology, publication, or human acceptance.")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument("--pipeline", type=Path, default=DEFAULT_PIPELINE)
    parser.add_argument("--feature-registry", type=Path, default=DEFAULT_REGISTRY)
    sub = parser.add_subparsers(dest="operation", required=True, parser_class=_Parser)
    for name in ("list", "search", "explain", "feature"):
        child = sub.add_parser(name)
        if name != "list":
            child.add_argument("value")
        child.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
        child.add_argument("--offset", type=int, default=0)
    child = sub.add_parser("current-project")
    child.add_argument("--authority", type=Path)
    child.add_argument("--sha256")
    child.add_argument("--pointer", type=Path)
    child.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    try:
        args = parser.parse_args(argv)
        if args.operation == "current-project":
            result = current_project(args.authority, args.sha256, args.pointer, args.limit)
        else:
            result = query(discover(args.pipeline, args.feature_registry), args.operation,
                           getattr(args, "value", None), args.limit, args.offset)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, SyntaxError) as exc:
        print(json.dumps(dict(status="failed", error=str(exc)), ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
