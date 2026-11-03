# SH16 example routing

| Sheets | Family | Applicable branches |
|---|---|---|
| 01 / 02 | schedule | source, parameters |
| 03 / 04 | plant_schematic | source, parameters, topology, visualization |
| 05 | architectural_support | source, architecture (maintenance paths are not pipes) |
| 06 / 07 | outdoor_plan | source, parameters, topology, architecture, visualization |
| 08 / 09 / 10 | ceiling_plan | source, parameters, topology, architecture, visualization |
| 11 | isometric | source, parameters, topology, visualization |

Sheet numbers are an example manifest, never an automatic filename classifier. Native source inventory and local evidence determine tags. 06/07 large equipment with unproven external contacts remains explicit pending; do not borrow schematic connectivity. Crossover arcs indicate independent pipes; relative over/under elevation is unknown. Straight gaps require verified crossover evidence; nearby real side branches must still become true T nodes after normalization. Preserve previous positive and negative regressions for overshoot false T, true short branches, equipment frames, layer-0 components, nested instruments and local Pair symbols.
