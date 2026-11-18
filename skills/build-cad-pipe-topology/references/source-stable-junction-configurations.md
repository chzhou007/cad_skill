# Reapply junction readers after equipment ownership changes

An equipment-owner rebuild can leave a source-aware junction configuration
pinned to the preceding graph. The direct three-ray reader may still work for
ordinary Ts while reviewed circles fail only because the configuration no longer
selects that graph. Do not replace the old configuration's hashes, drop its
lineage parents, broaden snapping, or interpret this error as a disconnected pipe.

Use `reconstruct-source-stable-junctions` and
`validate-source-stable-junctions` on a pinned source/configuration/current graph
manifest. `source_stable_junction_reapplication.prepare` is the shared guarded
reader for subsequent reconstruction consumers. The original readers remain
byte-exact. The generated configuration stays private to that reader; it is not
an unrestricted replacement for an old pipeline configuration.

The currently supported transition is the original complete native row-order
equipment-owner rebuild. Replay its original verifier, including its own local
topology parent and native equipment controls. Require its original graph,
source, component inventory and actual current graph to match the configuration
lineage. A different transition requires an explicit source owner adapter.

For each fallback, compare the complete T node, all three incident edge payloads
and their neighboring nodes. Retain IDs, Chinese source labels, floor, system,
paths, unknown parameters and original evidence. Even a small geometry change
or a different neighboring port blocks reuse. Then run the original native
reader on both graph versions and require equal three-ray evidence. The result
records the actual current graph hash and its old configuration provenance.
Geometry or ambiguous-ray errors never trigger this configuration fallback.

Batch every current T in the applicable floor plans, including nodes that already
work. Report recovered configurations separately from pre-existing native passes
and held scopes. A held node's incident edges cannot establish confirmed
cross-view connections through that node. An expert's marked extent does not
automatically cover a similar supply/return point elsewhere.

This gate restores a source-reading capability. It assigns no DN, physical
length or cross-view correspondence. In particular, a circle's drawn radius and
an actual gap around a valve remain unknown length even when its connectivity
is proved. Mixed edges retain separate 11-source vertical owners. Reapply the
appropriate path, component, unit and metric owners before attribute adoption;
configuration recovery alone does not increase the completed-edge count or
inherit human acceptance.
