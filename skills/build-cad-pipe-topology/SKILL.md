---
name: build-cad-pipe-topology
description: Convert HVAC, MEP, or P&ID piping drawings in DWG/DXF form into an auditable node-edge graph with equipment nodes, physical T-junctions, omission-symbol interfaces, and inline devices aggregated as edge attributes. Use for CAD topology extraction, schematic simplification, false/missing T diagnosis, exploded-symbol recovery, equipment reconnection, edge inventory generation, topology visualization, or regression/alignment testing against the bundled SH16 case.
---

# CAD 管网拓扑与双视图属性

Current release: **v1.17.79**

指令整理版：2026-11-18（v241.1）；代码版本不变。负责元素、连接语义、设备/端口、局部节点边、跨图映射和属性证据。

## 从当前阶段开始

多图任务先看 [完整流水线](../orchestrate-cad-drawing-pipeline/references/end-to-end-pipeline.md)。历史专题、脚本和反例完整保留在 [详细规则索引](references/detailed-rule-index.md)，按需读取，不重新逐例推理已确认规则。

专家确认多画圆圈时，先用 `scripts/verify_received_surplus_circle_disposition.py` 核对原答复、源圆/穿心直线及当前局部拓扑；多画圆不生成T、设备或端口，也不删除主管。该证据核验与接口归属规则分别处理。

原始 CAD 只读，保留源实体句柄、嵌套路径、WCS/OCS 变换、图层/颜色和版本。非 T3 优先，中文可读后才做语义判断。参数缺失保持未知。

## 拓扑依赖顺序

1. 原生图元、材料/图例、设备标签、外形、端口及管线候选。
2. 临时端点和方向/系统证据；执行共享几何归一化与有证据的断口/省略恢复。
3. 识别真实物理设备实例、独立供回水端口、真实 T、立管和已知去向边界。
4. 按已确认切点拆主管、重建边、重新归属边上元件及属性；保留源覆盖与旧新 ID 映射。
5. 逐类源 CAD 对照，覆盖同类群体及反例；局部图通过的范围才可作为正式跨图依据。
6. 先按轴测源路径分方向，仅水平属性范围进入平面对应；用两侧图结构批量匹配身份/端口/系统/路径，双向检查；回到错误所属阶段修复后重算。
7. 分方向融合属性，做源覆盖、设备保留、元件守恒、稳定 ID 和实际发布有效值检查。

临时端点不是设备，也不自动是最终待核节点。连接或端口变化后必须重算相邻 T/边、元件、映射和属性，不手改最终图掩盖上游错误。

## 不可丢失的规则

- 供回水独立。跨管的断画只恢复本管连续，普通无圆正交交叉不套圆环规则。
- 波浪表示长管绘图省略，两侧连续；不是软管、变径或额外物理属性，省略长度不推算。
- 断支路或疑似四通先找同系统主管上的孤立圆圈并核对隐藏重叠路径；不靠最近投影、圆图层或虚构相切点确立连接。
- 设备实例、端口、外形、标签分层存证；成套归并不删除真实设备，房名/包围框/距离不能单独证明端口归属。
- 阀门、仪表、软接等保留实例，唯一归边；镜像、负 OCS、嵌套变换要覆盖。源图局部错色依据已证明上游路径纠正并保留证据。
- DN 通过真实 T 和同系统连续路径继承，新标注/变径/冲突界定范围；支路 DN 不反向覆盖主管。F形顺序、旋转/镜像与中文楼层规则继续生效。
- **水平 DN/长度取正确匹配的平面；所有竖向（含同层升降）取轴测。** 按源路径方向拆分混合边，不以是否跨层分类。
- 轴测水平标注仅校验；未标竖管长度留空，不用默认层高、图面比例或水平 DN 括号值相减补长度。
- 重叠多管、复合 DN、环网分区保留成员身份；井区只定位，范围对应不冒充个体对应，共享总长不均分。

## 按需读取

| 处理内容 | 参考 |
|---|---|
| 原生读取与中文、显示边界 | [native-visible-bounds-and-wave-terminals](references/native-visible-bounds-and-wave-terminals.md) |
| 归一化、源覆盖、设备和元件守恒 | [normalization-v17](references/normalization-v17.md)、[methodology](references/methodology.md) |
| 平面隐藏重叠、圆圈/主管及源路径 | [plan-overlap-hidden-branches](references/plan-overlap-hidden-branches.md)、[plan-circle-source-paths](references/plan-circle-source-paths.md) |
| 波浪和同类群体批处理 | [wave-main-cohort-rules](references/wave-main-cohort-rules.md) |
| 原图对照、设备及端口归并 | [source-semantic-reconciliation](references/source-semantic-reconciliation.md) |
| DN 继承与分区 | [plan-DN-inheritance-and-extents](references/plan-DN-inheritance-and-extents.md)、[reviewed-alternative-ring-partition](references/reviewed-alternative-ring-partition.md) |
| 水平/竖向来源与长度限制 | [axis-segment-attribute-sources](references/axis-segment-attribute-sources.md)、[axis-horizontal-annotation-validation-only](references/axis-horizontal-annotation-validation-only.md) |
| 节点边、源证据及计算范围 | [output-schema](references/output-schema.md)、[expert-roundtrip-v18](references/expert-roundtrip-v18.md) |
| 既有图族入口、批量映射及全部历史修复 | [detailed-rule-index](references/detailed-rule-index.md) |

## 执行与交付

共享入口包括 `scripts/build_ceiling_family.py`、`scripts/build_isometric_v17.py`；按图族及参考文档选择配置。双视图已有 `scripts/batch_apply_crossview_rules.py`、`scripts/match_source_checked_crossview_paths.py` 及属性合成入口，先覆盖完整适用群体，再集中列出真实冲突。

保留型 CAD 转换默认交付查看器；总控统一组织显示时使用 `--without-visualization`，避免重复生成。查看器由相邻 Skill 负责，不在截图上另推一套图。

历史 feature 与新修复共同回归；单测、原生重建、整图/双视图、跨项目及 HIL 分开报告。未知不能填零；未解决区域保留具体原因和原图证据。相关语义变化后使旧确认失效，批注留作历史。
