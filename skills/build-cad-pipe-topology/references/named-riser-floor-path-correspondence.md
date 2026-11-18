# Named floor-riser interface/path correspondence

`match_named_riser_floor_paths.py` handles a different evidence pattern from the
existing three-device main-order rule. Require both independent services of one
equipment to have passed the native branch inventory in both views, plus one
explicit native named riser per service. Same equipment names or DN values alone
cannot match a path.

Replay native TEXT/underline/leader evidence on both sides. The plan target is
the selected floor's existing RIF circle, with one incident same-system path.
An axis name that points into a drawing-only air-vent leg must first replay the
historical normalization with explicit source layers in a private namespace.
The surviving original upper bend must identify exactly one checked through-
riser column and its actual middle T. Do not restore the removed leg or a T.

For this entry, each approach must be one existing edge: plan RIF to the checked
equipment main T, and axis riser middle T to the independently checked axis
equipment main T. The axis approach must be the actual non-through branch of
the riser contract. Replay complete native LINE coverage and current T rays.
Other multi-edge or ambiguous paths need their own source-backed extension;
this entry does not choose an endpoint by distance or a network-wide search.

Select main/detail label scope explicitly and retain the original policies.
A repeated identifier in the selected scope, competing normalized core, wrong
floor/system or changed service trace blocks the match. The riser DN stage is
used for its native column/T contract, never to prove identity by equal DN.

Output records map logical drawing interfaces and existing paths. Neither local
graph is changed. Keep physical ports unverified, circle radius excluded from
physical length, and DN/length fusion pending. Use
`pipeline.py validate-named-floor-riser-paths --mapping-run ...` for independent
source replay; success remains pending/exit 2 for the remaining stages.

SH16's first scope is second-floor CHWS1/CHWR1: RIF001/RIF002 correspond to
T123/T124, and approaches E0131/E0048 correspond to E0300/E0179 through the
independently checked CRAH-4#-2-2 service Ts. This closes two selected logical
interface/path correspondences, not all twelve floor-riser interfaces, metrics
or human acceptance. Run `test_match_named_riser_floor_paths.py`,
`test_named_floor_riser_mapping_gate.py`, native naming/normalization and
historical service-path tests before consuming the result.
