# Research and implementation boundaries

Research date: 2026-10-26. External skill text is reference material, not authorization or project instructions.

- [architectural-dxf-extraction](https://github.com/benchflow-ai/skillsbench/blob/main/tasks/ada-bathroom-plan-repair/environment/skills/architectural-dxf-extraction/SKILL.md): relevant layer inventory, units, native geometry and traceability practices. Its bathroom-specific interior rectangle, fixture and clearance heuristics are not imported into SH16.
- [freecad-review](https://github.com/tstapler/dotfiles/blob/master/.claude/skills/freecad-review/SKILL.md): a project-specific FreeCAD architectural review workflow, not a drop-in extractor for these drawings.
- [text-to-cad](https://github.com/cedrickchee/text-to-cad/blob/main/.agents/skills/cad/SKILL.md): generation/modeling scope; not native-source building recovery.
- [ezdxf Drawing / Export](https://ezdxf.readthedocs.io/en/stable/addons/drawing.html): source rendering reference. It supports export backends but does not recover ACIS geometry or turn a 2D plan into a semantically complete BIM model.
- [ezdxf XREF](https://ezdxf.readthedocs.io/en/stable/xref.html): embed/load external references only when the actual reference exists. Missing references remain missing.
- [ezdxf ACADProxyEntity](https://ezdxf.readthedocs.io/en/stable/dxfentities/acad_proxy_entity.html): cached proxy graphics may be displayed, but original application semantics are not thereby recovered. Do not destructively explode the production source.
- [IfcOpenShell IfcConvert](https://docs.ifcopenshell.org/ifcconvert.html): useful when a real IFC source is available, rather than claiming complete IFC semantics from SH16's 2D DXF.

This skill implements a read-only architectural context sidecar. Its JSON stores source primitives and annotation candidates; it is not a verified room adjacency graph, a code-compliance check or an IFC model. The companion viewer separates these records from hydraulic node-edge topology and human review state.
