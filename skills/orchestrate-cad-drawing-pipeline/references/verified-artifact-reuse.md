# Reuse a complete source-qualified native artifact

Use `pipeline.py reuse-native-artifact` for an unchanged completed member or
noncompound-main artifact. This is a separate **application** entry, not a
substitute status for `validate-*`. It avoids reconstructing the same fixed
ancestry for repeated inspection, attribute consumers and delivery checks.

```powershell
python -X utf8 -B pipeline.py reuse-native-artifact `
  --owner rebuild_noncompound_main_extents `
  --native-run ABSOLUTE_NATIVE_RUN `
  --cache-root ABSOLUTE_LOCAL_CACHE `
  --output NEW_EXECUTION_DIRECTORY
```

The first call executes the original complete verifier. It compares the entire
original JSON bytes, captures and merges every observed transitive file,
directory, existence probe and owned-scratch dependency, and refuses to store
untracked external side effects. It binds the complete four skill trees,
Python interpreter/DLL/library bytes, environment digest, working directory and
import path. Raw environment values are not written.

Later calls hash **current bytes** with up to16 I/O workers. Same length and
timestamp do not qualify changed data. New/missing dependencies, code, library,
environment, changed native proof or damaged capsules cause a fresh original
verification; a failing original verification cannot return an old result.
Live scratch roots block reuse. A late dependency change fails the application.
Cache data is JSON; no disk pickle or shell command is executed.

The optional default plot-style loader can attempt a literal empty filename.
Record this as a negative read and repeat its `FileNotFoundError` check; it is
not a read of the current directory. All nonempty reads and all external writes
keep the full original dependency rules.

Keep the cache and new execution output outside the original native proof
directory. Each call writes byte-identical `proof.json` and `execution.json`:

- `native_replay_performed:true`: original complete replay this invocation.
- `dependency_checked_reuse:true`: prior complete artifact, current byte closure
  checked; **not a new native replay** and not human acceptance.

Use `--force-native` for milestone cold controls and new rule qualification.
Unknown owners keep their original entries. A new input or rule still requires
reconstruction; warm reuse speed is not a cold-build speedup. Do not silently
enable this policy inside original verifier receipts or inherit HIL from it.
Measure both process startup-to-exit and owner execution, include final cleanup,
and compare whole native proof bytes. Do not invent CPU/RAM utilization targets.
