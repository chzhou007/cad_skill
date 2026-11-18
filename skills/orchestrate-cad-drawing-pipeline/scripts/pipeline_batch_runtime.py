"""Hash-bound stage DAG execution using the existing native subprocess owner.

Commands are explicit argument arrays. ``{stage_output}`` resolves to this
stage's isolated artifacts root; ``{stage_output:ID}`` reads a declared ancestor.
Declare input and implementation files as absolute-path -> SHA256 mappings.
Implementation must include the complete owner/configuration closure and
``cacheable:true`` must explicitly confirm relocatable, side-effect-free outputs
to enable resume; other stages execute normally without supplying cached stages.
Resume always creates a new run and copies verified artifacts, never changes a
historical run or represents cached artifacts as a cold reconstruction.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

import run_native_task_batch as native


SCHEMA = 1
TERMINAL = {"succeeded", "failed"}
SUCCESS = {"succeeded", "cached"}
DEFAULT_CORES = min(22, max(1, (os.cpu_count() or 2) - 2))
_STARTED_PROCESSES = {}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf8")).hexdigest()


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    os.replace(temporary, path)


def _inside(path, parent):
    return path == parent or parent in path.parents


def _no_link(path):
    path = Path(path)
    if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
        raise ValueError("linked artifact/input is not supported: " + str(path))


def _locks(mapping, label, observed=None):
    if not isinstance(mapping, dict):
        raise ValueError(label + " must be an absolute-path/SHA256 mapping")
    normalized = {}
    for value, expected in mapping.items():
        path = Path(value)
        if not path.is_absolute() or not re.fullmatch(r"[0-9a-f]{64}", str(expected)):
            raise ValueError(label + " requires absolute paths and lowercase SHA256")
        _no_link(path)
        path = path.resolve()
        key = str(path)
        if observed is not None and key in observed:
            actual = observed[key]
        else:
            actual = sha(path) if path.is_file() else None
            if observed is not None:
                observed[key] = actual
        if actual != expected:
            raise ValueError(label + " changed: " + str(path))
        normalized[str(path)] = expected
    return normalized


def _check_locks(mapping, observed=None):
    for path, expected in mapping.items():
        if observed is not None and observed.get(path) == expected:
            continue
        _no_link(path)
        if not Path(path).is_file() or sha(path) != expected:
            raise ValueError("pinned file changed: " + path)
        if observed is not None:
            observed[path] = expected


def _artifact(path, root):
    """Hash actual bytes and complete directory membership, including empties."""
    path = Path(path)
    _no_link(path)
    if path.is_file():
        return {"path": str(path), "relative_path": path.relative_to(root).as_posix(),
                "kind": "file", "sha256": sha(path), "bytes": path.stat().st_size,
                "file_count": 1}
    if not path.is_dir():
        raise ValueError("declared artifact missing: " + str(path))
    members = []
    size = count = 0
    for child in sorted(path.rglob("*")):
        _no_link(child)
        if not _inside(child.resolve(), path.resolve()):
            raise ValueError("artifact escaped its owner directory")
        rel = child.relative_to(path).as_posix()
        if child.is_file():
            length = child.stat().st_size
            members.append([rel, "file", sha(child), length])
            size += length
            count += 1
        elif child.is_dir():
            members.append([rel, "directory"])
        else:
            raise ValueError("unsupported artifact member: " + str(child))
    return {"path": str(path), "relative_path": path.relative_to(root).as_posix(),
            "kind": "directory", "sha256": _digest(members), "bytes": size,
            "file_count": count}


def _artifacts(row):
    return [_artifact(path, Path(row["artifact_root"])) for path in row["outputs"]]


def _content(artifacts):
    return [{key: value for key, value in item.items() if key != "path"} for item in artifacts]


def _environment_digest():
    # Bind inherited settings without putting credentials or environment values on disk.
    return _digest(dict(os.environ))


def _prepare(manifest_path, output, cores):
    manifest_path = Path(manifest_path).resolve()
    output = Path(output).resolve()
    manifest = _read(manifest_path)
    if manifest.get("schema_version") != SCHEMA or not manifest.get("jobs"):
        raise ValueError("schema_version:1 and nonempty jobs required")
    budget = cores if cores is not None else manifest.get("core_budget", DEFAULT_CORES)
    if type(budget) is not int or not 1 <= budget <= 32:
        raise ValueError("core budget must be 1..32")
    observed = {}
    common = _locks(manifest.get("implementation", {}), "implementation", observed)
    runtime = {str(Path(__file__).resolve()): sha(__file__),
               str(Path(native.__file__).resolve()): sha(native.__file__)}
    ids = [row.get("id") for row in manifest["jobs"]]
    if any(not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", ident)
           for ident in ids) or len(set(ids)) != len(ids):
        raise ValueError("unique safe stage IDs required")
    raw_jobs = {row["id"]: row for row in manifest["jobs"]}
    ancestors = {}

    def visit(ident, active):
        if ident in active:
            raise ValueError("stage dependency cycle")
        if ident in ancestors:
            return ancestors[ident]
        deps = raw_jobs[ident].get("depends_on", [])
        if not isinstance(deps, list) or len(set(deps)) != len(deps):
            raise ValueError("depends_on must contain distinct IDs")
        found = set()
        for dep in deps:
            if dep not in raw_jobs:
                raise ValueError("unknown stage dependency: " + str(dep))
            found.add(dep)
            found.update(visit(dep, active | {ident}))
        ancestors[ident] = found
        return found

    for ident in ids:
        visit(ident, set())
    jobs = []
    pinned = {str(manifest_path): sha(manifest_path), **common, **runtime}
    for raw in manifest["jobs"]:
        ident = raw["id"]
        root = output / "stages" / ident / "artifacts"

        def expand(value):
            if not isinstance(value, str):
                raise ValueError("command/output values must be strings")
            def replace(match):
                dep = match.group(1)
                if dep not in ancestors[ident]:
                    raise ValueError("stage output reference requires ancestor dependency: " + dep)
                return str(output / "stages" / dep / "artifacts")
            value = re.sub(r"\{stage_output:([A-Za-z0-9_-]+)\}", replace, value)
            return value.replace("{stage_output}", str(root)).replace("{run_output}", str(output))

        command = raw.get("command")
        if not isinstance(command, list) or not command:
            raise ValueError("explicit command argument array required")
        command = [expand(value) for value in command]
        executable = Path(command[0])
        if not executable.is_absolute() or not executable.is_file():
            raise ValueError("command executable must be an existing absolute file")
        inputs = _locks(raw.get("inputs", {}), "inputs", observed)
        implementation = {**common, **_locks(raw.get("implementation", {}), "implementation", observed)}
        try:
            executable_digest = sha(executable)
        except OSError:
            # Microsoft Store's current-interpreter alias is executable but is
            # not an ordinary readable file. Bind and launch its real package binary.
            if executable != Path(sys.executable):
                raise
            executable = Path(sys.base_prefix) / Path(sys.executable).name
            executable_digest = sha(executable)
            command[0] = str(executable)
        command_files = {str(executable.resolve()): executable_digest}
        for arg in command[1:]:
            candidate = Path(arg)
            try:
                if candidate.suffix.lower() in {".py", ".exe", ".cmd", ".bat", ".ps1"} and candidate.is_file():
                    command_files[str(candidate.resolve())] = sha(candidate)
            except OSError:
                pass  # An inline program or ordinary argument need not be a valid filesystem path.
        outputs = raw.get("outputs", ["{stage_output}"])
        if not isinstance(outputs, list) or not outputs:
            raise ValueError("each stage must declare nonempty outputs")
        destinations = []
        for value in outputs:
            dest = Path(expand(value))
            if not dest.is_absolute():
                dest = root / dest
            dest = dest.resolve()
            if not _inside(dest, root):
                raise ValueError("stage outputs must stay under " + str(root))
            destinations.append(str(dest))
        locks = {**inputs, **implementation, **command_files, **runtime}
        cwd = Path(raw.get("cwd", ""))
        if not cwd.is_absolute() or not cwd.is_dir():
            raise ValueError("stage cwd must be an existing absolute directory")
        row = {"id": ident, "command": command, "cwd": str(cwd.resolve()),
               "cores": raw.get("cores", 1), "depends_on": raw.get("depends_on", []),
               "success_exit_codes": raw.get("success_exit_codes", [0]), "inputs": locks,
               "outputs": destinations, "artifact_root": str(root),
               "implementation_declared": bool(implementation), "cacheable": raw.get("cacheable", False),
               "specification": {"command": raw["command"], "cwd": str(cwd.resolve()),
                                 "cores": raw.get("cores", 1), "depends_on": raw.get("depends_on", []),
                                 "outputs": outputs, "success_exit_codes": raw.get("success_exit_codes", [0]),
                                 "locks": locks, "cacheable": raw.get("cacheable", False)}}
        if type(row["cacheable"]) is not bool:
            raise ValueError("cacheable must be boolean")
        jobs.append(row)
        pinned.update(locks)
    # The native owner supplies structural/budget validation. All pins were
    # freshly checked above; avoid rereading shared thousands-file closures once
    # per stage during this single planning snapshot. Execution rechecks pins.
    native.validate({"schema_version": 1, "jobs": [dict(row, inputs={}) for row in jobs]}, budget)
    for row in jobs:
        for value in row["outputs"]:
            destination = Path(value)
            for path in pinned:
                source = Path(path)
                if _inside(source, destination) or _inside(destination, source):
                    raise ValueError("output overlaps a pinned input or implementation: " + path)
    return {"schema_version": SCHEMA, "manifest": {"path": str(manifest_path), "sha256": sha(manifest_path)},
            "manifest_content_sha256": _digest(manifest), "runtime_locks": runtime,
            "environment_sha256": _environment_digest(), "core_budget": budget,
            "output": str(output), "jobs": jobs}


class _State:
    def __init__(self, output, value, notify=None):
        self.output, self.value, self.notify = Path(output), value, notify

    def commit(self, event, stage=None):
        self.value["revision"] += 1
        _write(self.output / "status.json", self.value)
        change = {"revision": self.value["revision"], "event": event,
                  "status": self.value["status"]}
        if stage is not None:
            change.update(stage=stage, stage_status=self.value["stages"][stage]["status"])
        with (self.output / "events.jsonl").open("a", encoding="utf8") as stream:
            stream.write(json.dumps(change, ensure_ascii=False) + "\n")
        if self.notify:
            self.notify(change)


def _process_info(pid):
    """Return alive/creation identity without signalling or killing a Windows PID."""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = kernel.OpenProcess(0x1000, False, pid)
            if not handle:
                return {"alive": False if ctypes.get_last_error() == 87 else None, "identity": None}
            try:
                code = wintypes.DWORD()
                if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return {"alive": None, "identity": None}
                stamps = [wintypes.FILETIME() for _ in range(4)]
                token = None
                if kernel.GetProcessTimes(handle, *(ctypes.byref(stamp) for stamp in stamps)):
                    token = str((stamps[0].dwHighDateTime << 32) | stamps[0].dwLowDateTime)
                return {"alive": code.value == 259, "identity": token}
            finally:
                kernel.CloseHandle(handle)
        os.kill(pid, 0)
        proc = Path("/proc") / str(pid) / "stat"
        token = proc.read_text().rsplit(")", 1)[1].split()[19] if proc.is_file() else None
        return {"alive": True, "identity": token}
    except ProcessLookupError:
        return {"alive": False, "identity": None}
    except (OSError, ValueError, IndexError):
        return {"alive": None, "identity": None}


def _record_executor_failure(run, state, message):
    state.update(status="failed", error={"type": "ExecutorUnavailable", "message": message})
    for row in state["stages"].values():
        if row["status"] in {"pending", "running"}:
            row.update(status="interrupted", error={"message": message})
    state["failures"] = [ident for ident, row in state["stages"].items() if row["status"] not in SUCCESS]
    state["summary"] = str(run / "summary.json")
    _write(run / "summary.json", dict(state, revision=state["revision"] + 1))
    _State(run, state).commit("executor_unavailable")
    return state


def _recover_dead_executor(run, state):
    if state["status"] not in {"planned", "running"}:
        return state
    launch = _read(run / "launch.json") if (run / "launch.json").is_file() else {}
    pid = state.get("executor_pid", launch.get("pid"))
    expected = state.get("executor_identity", launch.get("identity"))
    if not pid:
        return state
    observation = _process_info(pid)
    lost = observation["alive"] is False or (expected and observation["identity"] and expected != observation["identity"])
    if not lost:
        return state
    # Multiple read-only clients may discover the same vanished owner. Only one
    # observer records this real failure transition; ordinary polls never write.
    recovery = run / "recovery.lock"
    try:
        with recovery.open("x", encoding="utf8") as stream:
            stream.write(str(os.getpid()))
    except FileExistsError:
        return _read(run / "status.json")
    try:
        state = _read(run / "status.json")
        if state["status"] not in {"planned", "running"}:
            return state
        return _record_executor_failure(run, state, "Executor exited without a verified terminal summary; child outputs remain unverified")
    finally:
        recovery.unlink(missing_ok=True)


def plan_manifest(manifest_path, output, cores=None):
    """Validate/pin a DAG and create a new planned run without launching owners."""
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError("choose a new run directory: " + str(output))
    plan = _prepare(manifest_path, output, cores)
    output.mkdir(parents=True)
    _write(output / "manifest.lock.json", plan)
    state = {"schema_version": SCHEMA, "revision": 0, "status": "planned", "output": str(output),
             "manifest_sha256": plan["manifest"]["sha256"],
             "plan_sha256": sha(output / "manifest.lock.json"), "core_budget": plan["core_budget"],
             "peak_allocated_core_slots": 0, "stages": {row["id"]: {"id": row["id"], "status": "pending"}
                                                       for row in plan["jobs"]},
             "human_accepted": False, "whole_goal_complete": False}
    _State(output, state).commit("planned")
    return query_status(output)


def _signature(plan, row, completed):
    deps = {ident: {"signature": completed[ident]["signature"],
                    "artifacts": _content(completed[ident]["artifacts"])} for ident in row["depends_on"]}
    return _digest({"specification": row["specification"], "dependencies": deps,
                    "environment_sha256": plan["environment_sha256"]})


def _check_dependencies(row, jobs, completed):
    remaining, checked = list(row["depends_on"]), set()
    while remaining:
        ident = remaining.pop()
        if ident in checked:
            continue
        checked.add(ident)
        if _content(_artifacts(jobs[ident])) != _content(completed[ident]["artifacts"]):
            raise ValueError("dependency artifacts changed: " + ident)
        remaining.extend(jobs[ident]["depends_on"])


def _execute(row, output, jobs, completed):
    try:
        _check_dependencies(row, jobs, completed)
        result = native.execute(row, output / "logs")
        _check_dependencies(row, jobs, completed)
        if result["status"] != "passed":
            return {**result, "status": "failed", "execution": "executed", "artifacts": []}
        return {**result, "status": "succeeded", "execution": "executed", "artifacts": _artifacts(row)}
    except Exception as exc:
        return {"id": row["id"], "status": "failed", "execution": "executed", "artifacts": [],
                "error": {"type": type(exc).__name__, "message": str(exc)}}


def _previous(run):
    if run is None:
        return None
    run = Path(run).resolve()
    summary = _read(run / "summary.json")
    if summary.get("status") not in TERMINAL or summary.get("plan_sha256") != sha(run / "manifest.lock.json"):
        raise ValueError("resume source is not a completed hash-bound run")
    return run, summary


def _reuse(previous, row, signature):
    if previous is None:
        return None, "no_resume_source"
    if not row["cacheable"] or not row["implementation_declared"]:
        return None, "implementation_closure_not_declared_or_cache_disabled"
    run, summary = previous
    prior = summary.get("stages", {}).get(row["id"], {})
    if prior.get("status") not in SUCCESS:
        return None, "no_successful_stage"
    receipt_path = run / "receipts" / (row["id"] + ".json")
    if not receipt_path.is_file() or sha(receipt_path) != prior.get("receipt_sha256"):
        return None, "receipt_hash_mismatch"
    receipt = _read(receipt_path)
    if (receipt.get("id") != row["id"] or receipt.get("plan_sha256") != summary.get("plan_sha256")
            or receipt.get("manifest_sha256") != summary.get("manifest_sha256")):
        return None, "receipt_binding_mismatch"
    if receipt.get("signature") != signature or receipt.get("status") not in SUCCESS:
        return None, "input_implementation_or_dependency_hash_changed"
    prior_root = run / "stages" / row["id"] / "artifacts"
    try:
        for item in receipt.get("artifacts", []):
            path = Path(item["path"])
            if not _inside(path, prior_root):
                return None, "invalid_cached_artifact_path"
            if _content([_artifact(path, prior_root)]) != _content([item]):
                return None, "cached_output_hash_mismatch"
        if not receipt.get("artifacts"):
            return None, "missing_cached_artifacts"
        current = Path(row["artifact_root"])
        for item in receipt["artifacts"]:
            src = Path(item["path"])
            dst = current / item["relative_path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            if item["kind"] == "directory":
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        artifacts = _artifacts(row)
        if _content(artifacts) != _content(receipt["artifacts"]):
            raise ValueError("copied artifact hash mismatch")
        return {"id": row["id"], "status": "cached", "execution": "cached_artifact_copy",
                "exit_code": None, "artifacts": artifacts, "reused_from": str(receipt_path),
                "reused_receipt_sha256": sha(receipt_path), "cold_execution": False}, None
    except (OSError, ValueError) as exc:
        # A partly copied target is never reused or overwritten by an owner.
        if Path(row["artifact_root"]).exists():
            raise ValueError("cache copy failed; choose a new run directory: " + str(exc)) from exc
        return None, "cached_output_unavailable"


def run_manifest(manifest_path, output, cores=None, resume_from=None, notify=None):
    """Run/wait internally; only unchanged, byte-verified successes may be copied."""
    output = Path(output).resolve()
    if not output.exists():
        plan_manifest(manifest_path, output, cores)
    current = _read(output / "status.json")
    if current["status"] != "planned":
        raise ValueError("run directory already started; resume into a new directory")
    plan = _read(output / "manifest.lock.json")
    if sha(output / "manifest.lock.json") != current["plan_sha256"]:
        raise ValueError("planned manifest lock changed")
    fresh = _prepare(manifest_path, output, cores if cores is not None else plan["core_budget"])
    if fresh != plan:
        raise ValueError("planned inputs, implementation, environment or manifest changed")
    previous = _previous(resume_from)
    claim = output / "executor.lock"
    with claim.open("x", encoding="utf8") as stream:
        stream.write(str(os.getpid()))
    for folder in ("logs", "receipts", "stages"):
        (output / folder).mkdir(exist_ok=True)
    state = _State(output, current, notify)
    current.update(status="running", executor_pid=os.getpid(), executor_identity=_process_info(os.getpid())["identity"],
                   resume_from=str(previous[0]) if previous else None)
    state.commit("started")
    jobs = {row["id"]: row for row in plan["jobs"]}
    waiting, live, completed = set(jobs), {}, {}
    used = 0
    started = time.monotonic()

    def finish(ident, result):
        if "signature" not in result:
            result["signature"] = (_signature(plan, jobs[ident], completed)
                                   if all(dep in completed for dep in jobs[ident]["depends_on"]) else None)
        result.update(manifest_sha256=plan["manifest"]["sha256"], plan_sha256=current["plan_sha256"])
        receipt = output / "receipts" / (ident + ".json")
        _write(receipt, result)
        result = dict(result, receipt=str(receipt), receipt_sha256=sha(receipt))
        completed[ident] = result
        current["stages"][ident] = result
        state.commit("stage_finished", ident)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(plan["core_budget"], len(jobs))) as pool:
            while waiting or live:
                for ident, row in jobs.items():
                    if ident not in waiting:
                        continue
                    deps = row["depends_on"]
                    failed = [dep for dep in deps if dep in completed and completed[dep]["status"] not in SUCCESS]
                    if failed:
                        waiting.remove(ident)
                        # A blocked stage has no reusable execution signature.
                        finish(ident, {"id": ident, "status": "blocked_by_dependency", "signature": None,
                                       "execution": "not_run", "blocked_by": failed, "artifacts": []})
                        continue
                    if not all(dep in completed for dep in deps) or used + row["cores"] > plan["core_budget"]:
                        continue
                    waiting.remove(ident)
                    try:
                        _check_locks({plan["manifest"]["path"]: plan["manifest"]["sha256"]})
                        if previous and row["cacheable"] and row["implementation_declared"]:
                            _check_locks(row["inputs"])
                        _check_dependencies(row, jobs, completed)
                        signature = _signature(plan, row, completed)
                        reused, reason = _reuse(previous, row, signature)
                        if reused:
                            finish(ident, reused)
                            continue
                        Path(row["artifact_root"]).parent.mkdir(parents=True, exist_ok=True)
                        current["stages"][ident] = {"id": ident, "status": "running", "execution": "executed",
                                                       "signature": signature, "cache_miss_reason": reason,
                                                       "log": str(output / "logs" / (ident + ".log"))}
                        state.commit("stage_started", ident)
                        # Threads wait on isolated native subprocesses; CAD geometry remains in its owner process.
                        future = pool.submit(_execute, row, output, jobs, dict(completed))
                        live[future] = (ident, signature, reason)
                        used += row["cores"]
                        current["peak_allocated_core_slots"] = max(current["peak_allocated_core_slots"], used)
                    except Exception as exc:
                        finish(ident, {"id": ident, "status": "failed", "execution": "not_run", "artifacts": [],
                                       "error": {"type": type(exc).__name__, "message": str(exc)}})
                if not live:
                    if waiting:
                        raise RuntimeError("no stage can be scheduled")
                    break
                done, _ = concurrent.futures.wait(live, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    ident, signature, reason = live.pop(future)
                    used -= jobs[ident]["cores"]
                    result = future.result()
                    result.update(signature=signature, cache_miss_reason=reason)
                    finish(ident, result)
        # Verify immutable source/implementation and all retained artifacts again before reporting success.
        verified = {}
        for ident, row in jobs.items():
            if completed[ident]["status"] not in SUCCESS:
                continue
            try:
                _check_locks({plan["manifest"]["path"]: plan["manifest"]["sha256"], **row["inputs"]}, verified)
                _check_dependencies(row, jobs, completed)
                if _content(_artifacts(row)) != _content(completed[ident]["artifacts"]):
                    raise ValueError("stage artifact changed after completion")
            except Exception as exc:
                finish(ident, {**completed[ident], "status": "failed", "error": {"type": type(exc).__name__, "message": str(exc)}})
        changed = True
        while changed:
            changed = False
            for ident, row in jobs.items():
                failed = [dep for dep in row["depends_on"] if completed[dep]["status"] not in SUCCESS]
                if failed and completed[ident]["status"] in SUCCESS:
                    finish(ident, {**completed[ident], "status": "invalidated_by_dependency", "blocked_by": failed})
                    changed = True
        current["status"] = "succeeded" if all(item["status"] in SUCCESS for item in completed.values()) else "failed"
    except Exception as exc:
        current.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
        for item in current["stages"].values():
            if item["status"] == "pending":
                item.update(status="blocked_by_executor", execution="not_run")
            elif item["status"] == "running":
                item.update(status="failed_executor", error={"message": "Executor could not preserve a verified completion receipt"})
    finally:
        current.update(elapsed_seconds=time.monotonic() - started,
                       executed_stage_count=sum(row.get("execution") == "executed" for row in current["stages"].values()),
                       cached_stage_count=sum(row.get("status") == "cached" for row in current["stages"].values()),
                       cold_execution=not any(row.get("status") == "cached" for row in current["stages"].values()),
                       persisted_verification_reuse=False, human_accepted=False, whole_goal_complete=False)
        current["failures"] = [ident for ident, row in current["stages"].items() if row["status"] not in SUCCESS]
        current["summary"] = str(output / "summary.json")
        # A terminal status always points to an already durable summary of that revision.
        _write(output / "summary.json", dict(current, revision=current["revision"] + 1))
        state.commit("completed")
    return current


def query_status(run, limit=20):
    """Bounded state query; reads never refresh the revision or write timestamps."""
    if type(limit) is not int or not 0 <= limit <= 100:
        raise ValueError("limit must be 0..100")
    run = Path(run).resolve()
    for pid, process in list(_STARTED_PROCESSES.items()):
        if process.poll() is not None:
            del _STARTED_PROCESSES[pid]
    state = _recover_dead_executor(run, _read(run / "status.json"))
    stages = list(state["stages"].values())
    counts = {}
    for row in stages:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    result = {key: state[key] for key in ("schema_version", "revision", "status", "output", "core_budget",
               "peak_allocated_core_slots", "executor_pid", "elapsed_seconds", "cold_execution", "cached_stage_count",
               "executed_stage_count", "summary") if key in state}
    result.update(stage_count=len(stages), counts=counts, omitted_stage_count=max(0, len(stages) - limit), stages=[],
                  status_file=str(run / "status.json"), events=str(run / "events.jsonl"),
                  human_accepted=False, whole_goal_complete=False)
    if "error" in state:
        result["error"] = str(state["error"].get("message", ""))[:500]
    for row in stages[:limit]:
        item = {key: row[key] for key in ("id", "status", "execution", "exit_code", "log", "receipt", "cache_miss_reason") if key in row}
        item["artifact_count"] = len(row.get("artifacts", []))
        if row.get("error"):
            item["error"] = str(row["error"].get("message", ""))[:500]
        if row.get("blocked_by"):
            item["blocked_by"] = row["blocked_by"][:10]
        result["stages"].append(item)
    return result


def wait_for_change(run, after_revision, timeout=30, limit=20):
    """Long-poll actual transitions, returning unchanged=true on timeout."""
    if type(after_revision) is not int or after_revision < 0 or not 0 <= timeout <= 3600:
        raise ValueError("nonnegative revision and timeout in 0..3600 required")
    deadline = time.monotonic() + timeout
    while True:
        state = query_status(run, limit)
        changed = state["revision"] > after_revision
        if changed or state["status"] in TERMINAL or time.monotonic() >= deadline:
            return dict(state, changed=changed)
        time.sleep(min(0.1, max(0, deadline - time.monotonic())))


def start_manifest(manifest_path, output, cores=None, resume_from=None):
    """Start a detached executor with file-backed logs and no visible Windows window."""
    output = Path(output).resolve()
    if not output.exists():
        plan_manifest(manifest_path, output, cores)
    if _read(output / "status.json")["status"] != "planned":
        raise ValueError("run directory already started")
    args = [sys.executable, "-X", "utf8", "-B", str(Path(__file__).resolve()), "run",
            "--manifest", str(Path(manifest_path).resolve()), "--output", str(output)]
    if cores is not None:
        args.extend(["--cores", str(cores)])
    if resume_from is not None:
        args.extend(["--resume-from", str(Path(resume_from).resolve())])
    with (output / "executor.log").open("x", encoding="utf8") as stream:
        # Pass the exact mapping used by the plan hash. On Windows, restoring
        # an empty os.environ value can remove it from the implicit OS environment.
        process = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                   env=dict(os.environ),
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                                   start_new_session=os.name != "nt")
    _STARTED_PROCESSES[process.pid] = process
    _write(output / "launch.json", {"pid": process.pid, "identity": _process_info(process.pid)["identity"]})
    return dict(query_status(output), launched_pid=process.pid, executor_log=str(output / "executor.log"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("plan", "run", "start"):
        child = sub.add_parser(name)
        child.add_argument("--manifest", type=Path, required=True)
        child.add_argument("--output", type=Path, required=True)
        child.add_argument("--cores", type=int)
        if name != "plan":
            child.add_argument("--resume-from", type=Path)
    for name in ("status", "wait"):
        child = sub.add_parser(name)
        child.add_argument("--run", type=Path, required=True)
        child.add_argument("--limit", type=int, default=20)
        if name == "wait":
            child.add_argument("--after-revision", type=int, required=True)
            child.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args(argv)
    try:
        if args.action == "plan":
            result = plan_manifest(args.manifest, args.output, args.cores)
        elif args.action == "start":
            result = start_manifest(args.manifest, args.output, args.cores, args.resume_from)
        elif args.action == "run":
            run_manifest(args.manifest, args.output, args.cores, args.resume_from,
                         notify=lambda event: print(json.dumps(event, ensure_ascii=False), flush=True))
            result = query_status(args.output)
        elif args.action == "status":
            result = query_status(args.run, args.limit)
        else:
            result = wait_for_change(args.run, args.after_revision, args.timeout, args.limit)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        return 1 if result["status"] == "failed" else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if args.action == "run" and (args.output / "status.json").is_file():
            state = _read(args.output / "status.json")
            if state.get("status") == "planned":
                _record_executor_failure(args.output.resolve(), state, str(exc))
        print(json.dumps({"status": "error", "error": {"type": type(exc).__name__, "message": str(exc)[:1000]}},
                         ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
