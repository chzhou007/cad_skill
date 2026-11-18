# Inherit the profiled single-tap instrumentation entry

Use `reconstruct-profiled-schematic` for a schematic source profile containing
`instrumentation.single_tap_rules`. This reuses the historical native recognizer
that was previously present only in the local LF20 06 profile wrapper. It is an
existing recognition rule entering a shared execution path, not a newly inferred
CAD convention.

The recognizer requires the configured native body class letter, one exact
leader to a permitted native main, and one complete tagged head reached by the
other exact leader. A nearby label, bare box, missing leader/head or ambiguous
multiple heads does not qualify. Measuring leaders never join hydraulic pipes.
Previously consumed symbols stay with the original assembly owner.

The entry composes the unchanged original schematic builder in a private
namespace. It does not patch original module globals, alter inherited byte
guards, mutate the source drawing, or promote unsupported components. Existing
source profiles supply all layer/block/tag/scale conditions. An absent rule
keeps the original behaviour; legacy local wrappers should remain lineage and
must not wrap the shared entry a second time.

Run the same geometry, parameter and profile arguments as `build_schematic.py`.
The output adds `profiled-instrumentation-rebuild.json` with source member IDs,
input/implementation hashes and the unchanged inherited recognition-body AST.
Source regions, repeated equipment-view roles, pipe DN/floors, source-reference
reconciliation and human acceptance remain separately owned stages.

For cross-project regression, compare native source/path identities before raw
generated graph IDs. Rebuilds can reorder numeric IDs; retain an exact unique
old-to-new evidence mapping and compare complete component ownership through it.
An unchanged edge count alone cannot establish the inheritance result.
