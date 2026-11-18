# Apply a uniform path DN without allocating its group length

A qualified cross-view path may contain several plan and axis edges whose
internal T identities are not individually paired. DN is intensive: if every
independent plan scope has the same known DN, that DN applies to each complete
horizontal axis child. Length is extensive: the group total cannot be copied or
divided between children without additional evidence. This extends the existing
complete-batch attribute reader; it does not establish new correspondence.

`scripts/uniform_path_group_DN_context.py` derives child domains using the
inherited `horizontal_domain` reader and the original fusion orientation policy.
Require the qualified source comparison, exact canonical/rendered graph hashes,
policy hash, source and mapping receipts, and same-floor T-to-T child geometry.
Every child and every plan DN record must qualify; a changing/unknown/conflicting
DN, mixed/vertical/partial child, repeated writer or changed receipt withholds
the group. Do not infer horizontal geometry from floor labels alone.

The refresh entry binds this context to the exact rendered graph and writes it
to the manifest. Browser bootstrap independently checks that graph hash before
the UI and CSV consume the context. Raw graphs, mappings, components and old
annotations remain unchanged; new semantic review identity invalidates old HIL.

Use `refresh_attribute_templates.py --group-policy POLICY` for a full-batch
viewer, in addition to its normal original-input arguments. The policy must
match the parent's `sourceHashes.full_batch_plan_policy`. Run independent
artifact replay, actual browser properties/CSV and native CAD checks before
publication. A source-side context with a placeholder rendered hash is only a
diagnostic, never a distributable viewer.

SH16 source diagnostic: CHAIN-F3-0001 and CHAIN-F3-0002 cover ten complete
horizontal children with DN250. Their group lengths remain unallocated. The
rule has positive and negative Python/JS tests; actual publication is a separate
checkpoint. Do not report these ten as newly mapped edges or complete lengths.
