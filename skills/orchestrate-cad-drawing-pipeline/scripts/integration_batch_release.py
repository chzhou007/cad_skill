"""Replay a fixed known-rule family through its real owners and publication.

This adapter schedules existing producers; it defines no CAD geometry rules.
The SH16 recipe covers the complete qualified member-contact family, followed
by all-edge directional projection and exact current-viewer conservation.
Historical parent receipts are replayed by their original frozen executables.
They are not promoted to fresh evidence by this adapter.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

SCHEMA = "cad_known_rule_release_recipe_v1"
SCRIPTS = Path(__file__).resolve().parent
SKILLS = SCRIPTS.parent.parent
TOPOLOGY = SKILLS / "build-cad-pipe-topology" / "scripts"
VIEWER = SKILLS / "visualize-cad-pipe-topology" / "scripts"
STAGES = (
    "member-native", "direction-native", "member-publish", "member-verify",
    "direction-publish", "editor-upgrade", "offline-upgrade", "compare",
)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": sha(path)}


def checked(binding):
    require(set(binding) == {"path", "sha256"}, "exact file binding required")
    path = Path(binding["path"])
    require(path.is_absolute() and path.is_file() and sha(path) == binding["sha256"],
            "fixed input changed: " + str(path))
    return path


def inventory(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
            and "startup-logs" not in p.relative_to(root).parts}


def read_recipe(path):
    recipe = load(path)
    require(recipe.get("schema") == SCHEMA, "known-rule release recipe required")
    require(recipe.get("scope") == "complete_member_contact_family_and_all_edge_preservation",
            "unsupported integration scope")
    for name in ("authority", "member_manifest", "publication_manifest", "input_lock"):
        checked(recipe[name])
    lock = load(recipe["input_lock"]["path"])
    for path_, digest in lock["files"].items():
        require(sha(path_) == digest, "pinned source or parent changed: " + path_)
    require(recipe.get("human_accepted") is False, "recipe cannot claim human acceptance")
    return recipe


def stage_plan(recipe_path, destination):
    """Emit scheduler tasks; heavy owners reserve their full internal budget."""
    recipe_path = Path(recipe_path).resolve()
    recipe = read_recipe(recipe_path)
    fixed = {str(recipe_path): sha(recipe_path), recipe["input_lock"]["path"]: recipe["input_lock"]["sha256"]}
    fixed.update(load(recipe["input_lock"]["path"])["files"])
    base = [sys.executable, "-X", "utf8", "-B", str(Path(__file__).resolve()),
            "stage", "--recipe", str(recipe_path), "--output", "{stage_output}"]
    specs = [
        ("member-native", [], []),
        ("direction-native", [], []),
        ("member-publish", ["member-native"], ["--member", "{stage_output:member-native}/native"]),
        ("member-verify", ["member-publish"], ["--parent", "{stage_output:member-publish}/viewer"]),
        ("direction-publish", ["member-verify", "direction-native"],
         ["--parent", "{stage_output:member-verify}/viewer", "--routing", "{stage_output:direction-native}/native"]),
        ("editor-upgrade", ["direction-publish"], ["--parent", "{stage_output:direction-publish}/viewer"]),
        ("offline-upgrade", ["editor-upgrade"], ["--parent", "{stage_output:editor-upgrade}/viewer"]),
        ("compare", ["offline-upgrade", "member-native", "direction-native"],
         ["--parent", "{stage_output:offline-upgrade}/viewer", "--member", "{stage_output:member-native}/native",
          "--routing", "{stage_output:direction-native}/native"]),
    ]
    implementation = {str(Path(__file__).resolve()): sha(__file__)}
    jobs = [dict(id=name, command=base + ["--name", name] + args, cwd=recipe["cwd"],
                 cores=16 if name in ("member-publish", "member-verify") else 1,
                 inputs=fixed, implementation=implementation, outputs=["{stage_output}"],
                 depends_on=deps, cacheable=False)
            for name, deps, args in specs]
    result = dict(schema_version=1, jobs=jobs, recipe=pin(recipe_path),
                  scope=recipe["scope"], minimum_core_budget=16,
                  cache_policy="no_cross_run_reuse_of_unenumerated_historical_parent_input_closure",
                  human_accepted=False, full_raw_reconstruction=False)
    destination = Path(destination).resolve()
    require(not destination.exists(), "fresh manifest output required")
    destination.parent.mkdir(parents=True, exist_ok=True)
    dump(destination, result)
    return result


def execute(entry, arguments, folder, label, cwd):
    command = [sys.executable, "-X", "utf8", "-B", str(entry), *map(str, arguments)]
    started = time.monotonic()
    print(json.dumps({"stage": label, "state": "running", "command": command}, ensure_ascii=False), flush=True)
    log = folder / (label + ".log")
    with log.open("x", encoding="utf8") as stream:
        proc = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                              env=dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1"),
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    result = dict(command=command, exit_code=proc.returncode, elapsed_seconds=time.monotonic() - started,
                  log=pin(log), entry=pin(entry))
    dump(folder / (label + "-execution.json"), result)
    require(proc.returncode == 0, "native owner failed; see " + str(log))
    return result


def validate_routing_coverage(graph, routing):
    """Completeness compares exact segment identities, not only census totals."""
    expected = {}
    for edge in graph["edges"]:
        for pi, path in enumerate(edge.get("attribute_paths", [])):
            for si in range(len(path) - 1):
                expected[(edge["edge_id"], pi, si)] = (path[si:si + 2], edge.get("system"))
    actual = {}
    for row in routing["records"]:
        key = (row["edge_id"], row["path_index"], row["segment_index"])
        require(key not in actual, "duplicate routed segment")
        actual[key] = (row["scope_points"], row.get("system"))
        require(row.get("connection_proved_by_direction") is False and row.get("physical_length_mm") is None
                and row.get("DN_assigned") is None and row.get("human_accepted") is False,
                "direction routing cannot assign connectivity, physical values or acceptance")
    require(expected == actual, "routed segments differ from complete current source paths")
    require({e["edge_id"] for e in graph["edges"]} == {e["edge_id"] for e in routing["edges"]},
            "routing omitted an edge")
    return len(actual)


def compare_values(before, after):
    def index(rows):
        result = {r["edge_id"]: r["values"] for r in rows}
        require(len(result) == len(rows), "duplicate effective edge")
        return result
    old, new = index(before), index(after)
    require(old.keys() == new.keys(), "effective edge inventory differs")
    changes = [eid for eid in old if old[eid] != new[eid]]
    require(not changes, "effective attribute values changed: " + ",".join(changes[:12]))
    return dict(edges=len(old), cells=sum(len(v) for v in old.values()), changed_edges=[])


def import_viewer_helpers():
    for root in (TOPOLOGY, VIEWER, SCRIPTS, SKILLS / "visualize-cad-pipe-topology" / "assets" / "viewer"):
        sys.path.insert(0, str(root))
    from refresh_reviewed_ring_partition_DN import effective
    from hil_server import identity
    return effective, identity


def compare_release(recipe, parent, member, routing, output):
    """Publish fresh metadata; preserve current annotation bytes only after equality."""
    effective, identity = import_viewer_helpers()
    current = Path(recipe["current_viewer"])
    parent, member, routing = map(Path, (parent, member, routing))
    source = load(current / "public/data/graph.json")
    rebuilt = load(parent / "public/data/graph.json")
    require(source == rebuilt and sha(current / "public/data/graph.json") == sha(parent / "public/data/graph.json"),
            "full source graph, nodes, edges, devices or components changed")
    counts = dict(edges=len(rebuilt["edges"]), nodes=len(rebuilt["nodes"]),
                  equipment=sum(n["node_type"] == "equipment" for n in rebuilt["nodes"]),
                  components=len(rebuilt["instances"]))
    require(counts == recipe["expected_counts"], "source graph census differs from fixed authority")
    route = load(routing / "axis-source-routing.json")
    segments = validate_routing_coverage(rebuilt, route)
    native = load(member / "plan-member-contact-context.json")
    members = sorted(r["axis_edge_id"] for r in native["records"])
    require(members == recipe["expected_member_edges"], "complete known member-contact family differs")
    current_m, rebuilt_m = load(current / "public/data/manifest.json"), load(parent / "public/data/manifest.json")
    require(current_m["attributeValueContext"] == rebuilt_m["attributeValueContext"],
            "current attribute context differs from formal republished family")
    require(identity(current_m) == identity(rebuilt_m), "semantic review identity changed")
    old, new = effective(current), effective(parent)
    values = compare_values(old, new)
    original_directional = load(current / "public/data/directional-pipe-attributes.json")
    fresh_directional = load(parent / "public/data/directional-pipe-attributes.json")
    require(original_directional["records"] == fresh_directional["records"], "directional values/scopes changed")
    require(sha(current / "public/data/edge-review-queue.json") == sha(parent / "public/data/edge-review-queue.json"),
            "remaining review queue changed")
    for section in ("edgeAttributeEditorFix", "offlineReviewSafety"):
        require(section in rebuilt_m, "current review editor or backup safety not republished")
    # Preserve the current user's annotations, not an earlier publication's copy.
    target = output / "viewer"
    shutil.copytree(parent, target, ignore=shutil.ignore_patterns("annotations", "startup-logs", "__pycache__", "*.pyc"))
    if (current / "annotations").exists():
        shutil.copytree(current / "annotations", target / "annotations")
    else:
        (target / "annotations").mkdir()
    require(inventory(current / "annotations") == inventory(target / "annotations"), "current annotations changed")
    # These are new execution bindings; no historical pass flag is copied as a new result.
    report = dict(schema="cad_known_rule_release_comparison_v1", status="passed", scope=recipe["scope"],
                  authority=recipe["authority"], current_viewer=str(current), published_viewer=str(target),
                  member_proof=pin(member / "plan-member-contact-context.json"),
                  routing_proof=pin(routing / "axis-source-routing.json"),
                  counts=counts, routed_segments=segments, member_edges=members,
                  effective_comparison=values, exact_raw_graph=True, exact_directional_records=True,
                  exact_attribute_context=True, exact_review_queue=True,
                  current_annotations=inventory(current / "annotations"),
                  current_annotations_preserved=True, semantic_review_identity=identity(rebuilt_m),
                  new_DN_values=0, new_lengths=0, human_accepted=False,
                  full_raw_reconstruction=False, whole_goal_complete=False,
                  verification_scope="native_member_family_and_original_parent_replay_plus_all_edge_value_conservation",
                  browser_interaction_retested=False)
    dump(output / "current-effective.json", new)
    dump(output / "comparison.json", report)
    return report


def run_stage(recipe_path, name, output, parent=None, member=None, routing=None):
    recipe = read_recipe(recipe_path)
    output = Path(output).resolve()
    require(name in STAGES, "unknown integration stage")
    require(not output.exists() or not any(output.iterdir()), "fresh isolated stage output required")
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    if name == "member-native":
        execute(TOPOLOGY / "reconstruct_plan_member_contact_context.py",
                ["--manifest", recipe["member_manifest"]["path"], "--output", output / "native"], output, name, recipe["cwd"])
    elif name == "direction-native":
        args = [arg for key in ("source", "graph", "policy") for arg in ("--" + key, checked(recipe["routing"][key]))]
        execute(TOPOLOGY / "axis_attribute_source_routing.py", args + ["--output", output / "native"], output, name, recipe["cwd"])
    elif name == "member-publish":
        require(member is not None, "fresh member source stage required")
        spec = copy.deepcopy(load(recipe["publication_manifest"]["path"]))
        spec["native_proof"] = str(Path(member).resolve() / "plan-member-contact-context.json")
        spec["port"] = recipe["port"]
        dump(output / "publication-manifest.json", spec)
        execute(VIEWER / "refresh_plan_member_contacts.py",
                ["--manifest", output / "publication-manifest.json", "--output", output / "viewer"], output, name, recipe["cwd"])
    elif name == "member-verify":
        require(parent is not None, "fresh formal publication required")
        # The original verifier writes sibling owner logs. Own that copy here so
        # downstream verification cannot mutate a scheduler-owned parent stage.
        shutil.copytree(parent, output / "viewer", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        execute(VIEWER / "refresh_plan_member_contacts.py", ["--verify-output", output / "viewer"], output, name, recipe["cwd"])
    elif name == "direction-publish":
        require(parent is not None and routing is not None, "native direction and verified publication required")
        execute(TOPOLOGY / "axis_attribute_source_routing.py", ["--verify-output", routing], output, "direction-independent", recipe["cwd"])
        execute(VIEWER / "enable_directional_pipe_attributes.py",
                ["--parent", parent, "--routing", Path(routing) / "axis-source-routing.json", "--output", output / "viewer", "--port", recipe["port"]],
                output, name, recipe["cwd"])
    elif name in ("editor-upgrade", "offline-upgrade"):
        require(parent is not None, "published parent required")
        entry = "upgrade_edge_attribute_editor.py" if name == "editor-upgrade" else "upgrade_offline_review_safety.py"
        execute(VIEWER / entry, ["--parent", parent, "--output", output / "viewer", "--port", recipe["port"]], output, name, recipe["cwd"])
    else:
        require(all(x is not None for x in (parent, member, routing)), "all fresh publication dependencies required")
        compare_release(recipe, parent, member, routing, output)
    # Fixed input/code drift during a potentially long original-owner replay is
    # independently rejected even when the owner returns success.
    read_recipe(recipe_path)
    receipt = dict(schema="cad_known_rule_release_stage_v1", stage=name, status="passed",
                   recipe=pin(recipe_path), implementation=pin(__file__), elapsed_seconds=time.monotonic() - started,
                   artifacts=inventory(output), human_accepted=False, full_raw_reconstruction=False)
    dump(output / "stage-receipt.json", receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--recipe", required=True, type=Path)
    plan.add_argument("--output", required=True, type=Path)
    stage = commands.add_parser("stage")
    stage.add_argument("--recipe", required=True, type=Path)
    stage.add_argument("--name", required=True, choices=STAGES)
    stage.add_argument("--output", required=True, type=Path)
    for arg in ("parent", "member", "routing"):
        stage.add_argument("--" + arg, type=Path)
    args = parser.parse_args(argv)
    if args.command == "plan":
        result = stage_plan(args.recipe, args.output)
        print(json.dumps(dict(manifest=str(args.output.resolve()), stages=len(result["jobs"]), minimum_core_budget=16)))
    else:
        result = run_stage(args.recipe, args.name, args.output, args.parent, args.member, args.routing)
        print(json.dumps({k: result[k] for k in ("stage", "status", "elapsed_seconds")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
