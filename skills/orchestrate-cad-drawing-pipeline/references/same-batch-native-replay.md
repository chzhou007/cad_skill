# Reuse one current native verification inside a source/viewer batch

`native_replay_session.py` provides an explicit in-process `replay_session`
context. The first `verify_once(directory, verifier)` calls the native verifier;
it cannot load a saved receipt as a substitute. Outside the context every call
runs the verifier. No cache survives the context or crosses processes.

The context observes actual file reads, directory enumeration and stat-only
presence/metadata checks. Before reuse it checks file content hashes, alias
targets, missing-file states, directory contents, metadata and the in-memory
environment/CWD signature. Changed dependencies invalidate the result and run
the verifier again. Writes, subprocess/network effects, unsupported reads or
unstable observations disable reuse. Exceptions are never cached. Consumers
receive private copies so ancestry list edits cannot mutate cached evidence.

The supported upper-floor source gate and viewer call `verify_once` for the
same topology-owner verifier. Run them in one bounded process context to avoid
two identical native ancestry replays. Preserve the ordinary source gate,
complete-parent issues and viewer checks. Reuse is a scheduling improvement;
it does not accept topology, lengths or human review.

Report actual native replay/reuse/invalidation counts. A batch without a reuse
must not claim a measured saving. Pin this module with the viewer's verifier
dependencies. Test changed source/metadata, optional-file appearance, directory
changes, environment, mutation isolation, errors, external effects and the real
source-gate/viewer dispatch combination. Full native rebuild and browser checks
remain separate from these tests.
