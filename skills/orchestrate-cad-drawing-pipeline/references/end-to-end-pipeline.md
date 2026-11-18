# CAD 完整流水线：原图 → 局部拓扑 → 双视图互证 → 属性 → 专家交付

这是多图建图、既有项目继续处理和跨项目回测的主流程。先按阶段选用已有规则，再阅读对应专题；不从逐个解释 case 重新开始。历史修复与新增规则同等验收。阶段执行使用显式配方和已有专业入口，不能把编排成功解释为所有图纸或人工验收完成。

## 入口、职责与三层结果

| 工作 | 负责 Skill | 产物边界 |
|---|---|---|
| 原生 DWG 分图（输入需要时） | `dwg-region-split` | 保留坐标、块和文字的 DWG/DXF，回转核验；不是拓扑推断 |
| 多图编排、版本与阶段检查 | `orchestrate-cad-drawing-pipeline` | 逐图任务、依赖、收据、回归矩阵与交付状态 |
| 参数基础、图元、设备端口、连接、映射与属性 | `build-cad-pipe-topology` | 可追溯的局部节点边、元件、源图对照、跨图对应和属性证据 |
| 建筑信息与井区候选 | `extract-cad-building-context` | 同坐标系建筑侧数据；不修改管网、确认房间或连接 |
| 显示、对照、HIL、人工修改与离线包 | `visualize-cad-pipe-topology` | 有效属性展示/导出、打标历史和可运行交付；不从截图推断新图 |

始终保留三层：① 每张平面图自己的局部拓扑；② 每张轴测图自己的局部拓扑；③ 引用前两层版本及哈希的跨图映射与融合结果。图纸 ID 与节点/边 ID 联合标识对象；不同图相同边号不代表同一管道。

每图默认独立建图、对照和验收。用户明确要求双视图系统集成时，另建派生融合任务，保留原图任务。SH16 当前项目以 08/09/10 为一至三层平面、11 为轴测展示锚点；其他中心按原图内容识别图族，不能照搬编号、源句柄、坐标或项目策略。

## 阶段、输出和检查点

| 阶段 | 做什么 | 输出及进入下一阶段的条件 |
|---|---|---|
| 0. 固定输入与继承范围 | 固定非 T3 优先的授权原图、原始 Skill、当前代码/策略、历史修复及专家答复；核实当前权威版本 | 输入/配置哈希、逐项 feature 台账、已有结果与当前结果两份基线；存在代码不写成已通过 |
| 1. 原图读取与可读性 | 必要时 DWG→DXF/分图；检查中文、字体、单位、WCS、图层/颜色、嵌套 INSERT、OCS、代理和缺失引用 | 源实体及问题清单、源图预览；中文乱码先处理。历史参考恢复与原图直接提取分开标识 |
| 2. 参数与元素基础 | 从材料表/图例建立设备和边上元件类别、符号、参数与变体；提取管线、圆圈、尺寸、文字、设备外形和端口候选；建筑侧数据可并行 | 来源绑定的实例候选、源路径与变换、参数未知状态、建筑/井区侧数据；不靠表格数量验收设备数 |
| 3. 几何归一化与连续性 | 以临时端点/方向/系统筛查断口、跨线桥、波浪省略、阀件显示支腿、近接点、圆环及隐藏重叠支路 | 有证据的连续性及规范化路径、未解决候选、每次修复记录；跨管只补本管，不接被跨管 |
| 4. 设备、端口、T 与构边 | 识别物理设备实例及其端口、真实 T、立管/已知去向边界；消化重复/误归并；在最终连接上拆分主管并构边、重新分配元件 | 局部 nodes/ports/edges、元件实例表、源覆盖和旧新 ID 对照；设备/元件守恒、供回水独立 |
| 5. 两视图分别做源图对照 | 平面与轴测各自核查设备、端口、支路、边界、元件及遗漏；同类算法缺陷整批处理，保留反例 | 当前局部图绑定的对照收据、可用范围及隔离范围。已知确定性错误回到阶段 1–4；不能原样推给 HIL |
| 6. 方向分类与图到图批量对应 | 先按轴测源路径分水平/竖向/未知；仅水平范围进入平面属性对应队列，竖向留在轴测，混合边分别处理。连接互证仍涵盖两图系统/立管接口；在可用范围以设备身份+独立供回水端口、楼层、立管、主支路/T顺序及元件序列匹配路径；重建主图—详图关系 | 一对一/一对多/多对一的路径对应、范围对应、竞争候选和证据；范围已匹配不冒充内部每条边已对应 |
| 7. 双向互证与纠错 | 比较两图设备及端口、分支、系统、楼层和立管连续性；允许详略不同，逐项解释差异 | 区分提取错、连接错、对应错、重复表达与原图矛盾；回到所属阶段修正，相关映射失效重算 |
| 8. 分方向属性与继承 | 使用已分类的水平/垂直/未知方向源路径范围，读取匹配平面与轴测属性，执行受标注边界约束的管径继承 | 每个方向的 DN、长度、单位、范围、来源、继承链与冲突；部分长度、范围总长及未知项保持各自含义 |
| 9. 正式发布与有效值核对 | 当前源图对照、设备/元件守恒及受影响历史/新增回归通过后，在完整现有属性读取链上接入新规则，核对实际页面、CSV/JSON、元件与源数据；从实际有效值重建缺口清单 | 新值确已进入显示及导出，旧值保留或有明确修正差异；原生重建通过不等于已发布；正式验收范围不得绕过前置门槛 |
| 10. 集中 HIL 与答复回灌 | 剩余原图歧义/冲突进入统一页面；给整图定位、大范围原CAD和局部原图/拓扑 Pair；接收与版本绑定的答复 | 专家答复、批注历史、已确认规则范围；答复接收→规则应用→原生回证→发布→验收分别记录 |
| 11. 回归、封版与分发 | 日常跑受影响测试，里程碑跑完整适用重建；SH16打磨后冻结规则去LF20回测；同步代码/Skill/测试、运行环境及离线包 | 新旧能力、局部/整图/跨项目分别有证据；实际解压启动、编辑、恢复、Pair和全网导出通过；人工验收独立 |

阶段 2 的参数、建筑分支和不同图的独立处理可并行；阶段 5 的轴测检查也可提前。正式映射仍依赖双方局部拓扑及源图对照。预览/诊断候选可以提前产生，但不能标成已确认对应。

`hil_ready=false`、未绑定端口或尚未解释的源冲突须保留具体原因和受影响范围，不能因页面可访问而宣称具备正式验收条件；诊断/专家问题页面可以呈现这些未解决项，但不冒充已通过的交付。回归随每次规则变更执行，阶段 11 是最终封版核验，而非首次测试。

## 已收敛的关键规则

### 边和节点的先后顺序

**原始图元 → 临时端点与候选 → 有证据的连续性归一化 → 设备/端口与真实 T 重检 → 按节点分段构边 → 元件/属性重新归属。**

临时端点是计算输入，不是设备，也不自动是最终待核节点。先把原始断头固化成边，会把画法省略误报为大量断联。后续发现接点时必须重建相邻边，特别是支路自身同时充当主管的情况：先按全部已证实切点分段，再定位子边并接入，不能只在显示层补线。

| 表达/问题 | 采用的规则与边界 | 详细规则 |
|---|---|---|
| 供回水正交跨越、短断口、ARC/bulge跨线桥 | 确认同一根管连续，交叉点不连另一系统；普通正交不能套圆环叠管规则 | [拓扑方法](../../build-cad-pipe-topology/references/methodology.md) |
| 波浪成对省略 | 表示管太长而省画，两侧同系统原路径连续；不是软管、变径或额外物理元件；省略部分长度未知 | [波浪省略批处理](../../build-cad-pipe-topology/references/wave-main-cohort-rules.md) |
| 断头、疑似四通、没有支路的孤立圆圈 | 优先找同系统主管上的候选圆，核对隐藏重叠支路；不取最近投影点、不造相切点/四通/漏画圆；圆图层不能单独决定系统 | [平面叠管与隐藏支路](../../build-cad-pipe-topology/references/plan-overlap-hidden-branches.md) |
| 设备归并与接口 | 设备实例—端口—外形—标注分别存证；成套边界不删除真实设备；房名、外包框或距离近不足以证明端口 | [源语义对照](../../build-cad-pipe-topology/references/source-semantic-reconciliation.md) |
| 系统颜色冲突 | 沿已证明的上游/主管与连通路径核对；局部错误颜色要保留原值和纠正证据；不得由颜色冲突把供回水接通 | [设备/支路与源图对照](../../build-cad-pipe-topology/references/source-semantic-reconciliation.md) |
| 阀门、仪表、软接、散件 | 元件归边且唯一归属，镜像/负OCS/嵌套变换参与识别；拆边后重分配，缺阻力参数保持未知 | [输出约定](../../build-cad-pipe-topology/references/output-schema.md) |
| F形管径与楼层 | 保留顺序对应及旋转/镜像、中文标注；楼层分界须用图纸已证实方向，不能只按整边跨层分类 | [拓扑方法](../../build-cad-pipe-topology/references/methodology.md) |
| 空调井/暖通井、多立管 | 井区只提供定位候选；以系统、编号、端口和路径证明对应，同井/近邻不等于连接 | [建筑与井区能力](../../extract-cad-building-context/SKILL.md) |
| 主图—详图、重复表达 | 候选先回证，再替代或去重；路径对应允许多个边，不复制计入设备/元件/长度；映射依赖独立锚点与连接证据 | [跨图诊断](../../build-cad-pipe-topology/references/detailed-rule-index.md#cross-view-route-diagnostics) |
| 双管重叠及环网分区 | 复合标注如DN300/DN200应分成员管路；按已确认立管和分区核对上/下环段，具体200或250仍取本图标注；不能从房间数量直接算DN | [环网分区复用](../../build-cad-pipe-topology/references/reviewed-alternative-ring-partition.md) |

既有确认不要求对同类清楚实例重复问专家。先运行覆盖完整适用群体的规则及其反例检查，再把竞争关系、缺源证据或原图矛盾集中提交。已撤销的解释保留为负例和历史，不能因“测试总数没变”继续采用。

### 双视图与属性归属

- 图匹配是主路径：用已有局部拓扑、设备身份、端口、系统和有序路径批量对应。图像用于核对源证据、定位矛盾与专家交流；不能以截图邻近替代拓扑对应。标签只是锚点之一，重名设备须通过楼层、端口和路径消歧。
- **水平管段 DN 与长度来自正确匹配的楼层平面图；所有竖直段来自轴测图本体，包括同一楼层内升降段。** 按源路径分段方向分类，不按整边“是否跨层”分类，也不直接按屏幕竖线分类。[分段来源规则](../../build-cad-pipe-topology/references/axis-segment-attribute-sources.md)
- DN 在已证明连通的同系统管路、真实 T 和已证明弯头范围内继承；新/F形标注、变径证据或冲突截断继承。完整支路都要检查，不能把下游支管DN反向当主管DN或忽略两套叠管。
- 轴测水平标注用于校验，不能反推未知竖段长度。竖段没有明确归属的长度证据就留空；不用图面比例、默认层高或水平DN括号值相减补值。[轴测长度边界](../../build-cad-pipe-topology/references/axis-horizontal-annotation-validation-only.md)
- 平面尺寸与管段须有明确端点/轴网/单位对应；分别保存源线长度、已绘路径、XY中心线、尺寸支持的完整长度与实际安装/净管长。部分投影、波浪省略、元件内部未给长度不能伪装整段实长；共享范围总长不按边数或轴测比例均分。
- 统一边属性为 `pipe_attributes.horizontal`、`.vertical`，各自有 DN、长度、适用性、状态、源观察和分段范围；未知方向单列。原设备与边元件保留。人工整边长度在 `whole_edge_manual` 单列，不自动分摊。[统一属性约定](../../visualize-cad-pipe-topology/references/directional-pipe-attributes.md)

### 变更、缓存与失效

| 改变 | 必须重算/重新核验 |
|---|---|
| 源文件、中文解码、图层/坐标变换 | 元素及受影响下游全部阶段 |
| 连续性、设备/端口归属、系统、T | 相邻边与元件归属、源对照、映射、DN继承、长度覆盖、融合、有效值清单与相关验收 |
| 标注/尺寸读取或对应范围 | 对应DN/长度及继承链、融合和导出；必要时回查连接 |
| 映射或主详图关系 | 依赖其身份的属性、去重、计量、显示与验收 |
| 实际属性值/语义 | 相关人工确认失效，批注保留历史；稳定ID变化附映射，不自动迁移确认 |
| 纯样式、启动或编辑器修复 | 验证语义数据与身份是否仍一致，保留批注；重新验证实际受影响交互 |

缓存只复用输入、代码、策略、依赖和实际文件读取范围均未变的产物；保留独立副本和原验证条件。旧的通过标记不是当前重建证据。按依赖安排并行任务、输出目录隔离、共享总进程预算；先跑完整同类群体，不做相互依赖的盲目并行。[性能及原生重放](native-execution-performance.md)

## 实际入口：从规则应用开始

以下是已有入口的导航，不是把所有命令串起来就能得到完整SH16最新图。具体配置/策略须绑定源图、父图、图族及当前规则；执行前看对应 `--help`，按 [阶段契约](contracts.md) 填收据。未知配置不能默认套SH16。

| 场景 | 已有入口（相对所属 Skill） |
|---|---|
| 当前状态、规则和真实命令查询 | 总控 `pipeline.py actions current-project --pointer POINTER` / `feature FEATURE_ID` / `search QUERY` / `explain COMMAND`；默认返回有界信息和证据路径，先查再定向读源码 |
| 已知规则批量执行与正式发布闭环 | 总控 `pipeline.py batch-release plan --help` 生成原生生产、独立验证、发布及全边有效值核对配方；`pipeline.py batch start --manifest MANIFEST --output NEW --cores N` 调度显式依赖；详见[执行与发布](batch-execution-and-publication.md) |
| 变化等待、失败定位与安全恢复 | 总控 `pipeline.py batch status --run RUN` / `wait --run RUN --after-revision N --timeout 30`；恢复使用新目录和 `--resume-from OLD`，只有哈希闭合且声明可缓存的成功阶段可复用 |
| 批次规划、阶段契约验证 | 总控 `scripts/pipeline.py plan --config BATCH.json --output NEW`；`validate --run RUN`；`scripts/verify_dependencies.py` |
| 历史能力、受影响测试 | 总控 `scripts/audit_historical_skill_inheritance.py`；`scripts/feature_impact.py --changed PATH --run --output NEW.json`；`assets/feature-registry.json` |
| 原图读取、平面/轴测局部构建 | 拓扑 `scripts/source_readability.py`；`scripts/build_ceiling_family.py`；`scripts/build_isometric_v17.py`；其他图族按原有路由 |
| 连续性修复、原图对照 | 拓扑 `scripts/source_semantic_reconciliation.py`、`scripts/plan_hidden_branch_circle_screen.py`、`scripts/reconstruct_source_reviewed_circle_junctions.py`；总控 `scripts/source_comparison_gate.py` |
| 图到图候选、批处理及正式映射 | 拓扑 `scripts/crossview_equipment_branch_inventory_v2.py`、`scripts/match_source_checked_crossview_paths.py`、`scripts/batch_apply_crossview_rules.py`；总控 `pipeline.py validate-crossview` / `validate-known-rule-batch` |
| 平面属性与轴测分段合成 | 拓扑 `scripts/compose_full_batch_plan_attributes.py`、`scripts/full_batch_axis_attribute_composition.py`；专门规则由feature台账与各参考文档选用 |
| 建筑、空调井/暖通井线索 | 建筑 `scripts/architecture_context.py`、`scripts/source_shaft_text_inventory.py`；已有上下文不能证明代理内容已全部识别 |
| 发布、有效值检查及统一方向属性 | 查看器 `scripts/build_visualization.py`、`scripts/enable_directional_pipe_attributes.py`；新规则使用对应 `refresh_*` 发布器及其独立验证器，重建当前有效值清单 |
| 专家答复与离线交付 | 总控 `pipeline.py receive-current-review-answers` / `package-current-review`；查看器 `scripts/package_current_review.py`、`scripts/upgrade_edge_attribute_editor.py`、`scripts/upgrade_offline_review_safety.py` |
| 答复导入后自动应用、重建、回归及发布 | 总控 `pipeline.py hil-feedback start --config PROJECT.json --output NEW`，使用明确规则目录与当前查看器；详见[答复回灌闭环](hil-feedback-closed-loop.md)；已有有效应用保留，只有新增冲突进入HIL |
| 独立任务并行 | 总控 `scripts/run_native_task_batch.py --manifest MANIFEST --output NEW --cores N --monitor`；缓存、进程和测试预算见性能文档 |

原有 `pipeline.py plan` 只冻结和路由任务；`validate` 是契约检查，退出0/2/1分别为通过/待完成/失败。新增 `batch` 执行明确声明的阶段，并阻断失败阶段的下游；`batch-release` 将已有原生所有者和正式发布者接入同一配方，不直接修改最终图。完整重建仍需要专业入口实际执行、源证据回证及每个依赖阶段的可追溯收据。

任务计划目前锁定根 `SKILL.md`、脚本和资产，不包含全部 `references`；详细文档由本次分发快照和ZIP哈希绑定。指令更新后新建计划，旧冻结包和旧计划保持原样，不能重写旧锁冒充旧版。

## 专家交付与不倒退的检查

1. 每条待核对象给出具体原因：缺属性、缺个体对应、范围总长未分配、原图歧义、或已确认技术错误；不要把它们全部称为错误节点。技术缺陷先修复，专家页只提交仍需判断的内容，旧答复按问题/源版本去重。
2. 专家页面有大范围原图定位、局部原CAD/当前拓扑Pair及问题高亮；集中一次处理，同一规则回灌批量重建。接收答复不等于已应用、更不等于全图通过。
3. 手工DN支持水平/垂直/整边范围，范围值优先；长度、备注单独保存，保留中文、原CAD值、历史及失败时未保存输入。实际有效值与CSV/JSON一致。[编辑与恢复约定](../../visualize-cad-pipe-topology/references/edge-review-and-manual-length.md)
4. 完整备份导入须恢复问题、人工DN、长度、备注和历史，校验数据集/版本后原子写入；替换范围明确，整图确认不自动继承。同版包的不同解压目录不能共用批注存储。不能仅测试“备份能导出”。
5. 交付含节点、边、端口/来源、元件、映射、统一属性、原图证据、Skill/脚本/测试及版本绑定。查看器包附可用隔离运行环境、诊断日志和启动入口；保留 `annotations`。实际完整解压后测试启动、保存/刷新/恢复、标签、Pair、全网导出。[当前结果打包](../../visualize-cad-pipe-topology/references/published-current-review-delivery.md)
6. 代码单测、单图原生重建、双视图对应/属性、实际查看器、LF20泛化与专家验收分别记状态。可运行离线查看包与“从原始输入重建全部最新结果的完整包”是两种交付，后者依赖 [原始重建输入闭合](raw-source-reconstruction-delivery.md)。

## 项目状态和下一步的读取方式

实际统计存项目权威清单和带哈希的证据，不能在通用Skill中写死为永久完成。继续已有项目时先通过显式项目指针读取权威清单，核对哈希；不按目录修改时间猜测最新版。先用有界查询获取局部图、映射/有效属性、待核清单、答复、查看器、回归和原始重建状态，需要时再读对应证据。长任务由执行器等待，模型读取实际阶段变化与失败摘要。

SH16作为当前主开发/正确性项目；LF20在SH16规则稳定冻结后运行适用图族与反例。LF20原图直接构建与历史参考恢复两条测试路径分别报告；共享规则改变后回归SH16。此项目优先级不是对所有新中心的通用限制。

每次汇报：历史feature的继承/失败/未验证；平面源图正确性；轴测独立检查、映射和分方向属性缺口；代码/Skill/分发一致性；实际回归与人工验收。不得用一个总体完成率掩盖这些不同状态。
