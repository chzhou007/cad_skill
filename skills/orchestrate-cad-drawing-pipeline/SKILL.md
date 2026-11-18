---
name: orchestrate-cad-drawing-pipeline
description: Route multi-drawing CAD conversion through equipment/material recognition, family-specific pipe topology, architectural context and HIL visualization. Use for new CAD batches, mixed drawing families, pipeline configuration or cross-skill regression and delivery. Each drawing remains an independent task; specialized skills own their outputs.
---

# CAD 全流程编排

Version: **1.3.0**

执行闭环版：2026-11-18。多图任务从这里开始，以规则族为批次，复用既有生产入口、校验器与发布器。先用精简查询定位能力，再执行固定输入的批次。

## 先读与职责

先读 [完整流水线](references/end-to-end-pipeline.md)，再按当前阶段读取专题。历史规则全文保留在 [详细规则索引](references/detailed-rule-index.md)，无需每轮全部载入。

- 每张原图独立解析、建图、对照和验收；明确要求跨图集成时，另建引用原图版本的派生结果。
- 参数/管路/设备/映射由 `build-cad-pipe-topology` 负责；建筑由 `extract-cad-building-context` 负责；显示及专家交付由 `visualize-cad-pipe-topology` 负责。
- 原始 CAD 只读。未知图族先识别能力与缺口，不自动套用 SH16 的坐标、句柄或配置。专用入口不递归调用总控。
- 历史 feature 与本轮修复同等阻断发布；代码存在、单测通过、原图回证、完整重建、跨项目回测、人工验收分别记账。

## 固定执行顺序

1. 固定来源、非 T3 版本、代码/配置和历史 feature 台账；中文正确可读是前置条件。
2. 提取原生图元、设备/材料参数、嵌套变换和文字；建筑/轴网/井区以独立侧数据保留。
3. 从临时端点分类恢复有证据的连续性：短断口、跨线桥、波浪省略、圆圈及隐藏叠管支路。
4. 重算设备/端口、真实 T 和边，重新归属元件；不能只在最终图补一条显示线。
5. 平面与轴测各自做源图对照；确定性同类错误整批修复，未解决范围隔离。
6. 先按轴测源路径分方向，仅水平范围进入平面属性对应；用已有拓扑、设备/端口、系统、楼层、立管和有序路径批量配对，允许一对多与多对一。
7. 双向互证；提取/连接错误返回所属阶段，映射与依赖属性失效重算。
8. 分方向融合 DN 和长度：水平来自正确匹配平面，所有竖向来自轴测；无可靠长度证据留空。
9. 当前源对照、守恒及受影响历史/新增测试通过后发布；检查实际有效值、页面与 CSV/JSON，不能以中间产物通过冒充已发布。
10. 剩余冲突集中 HIL，提供大范围定位和局部 Pair；答复变成规则/配置，再批量回灌。
11. 回归、冻结并分发代码/Skill/测试/数据/查看器；验收和原始输入全链复现独立报告。

## 按阶段读取

| 任务 | 参考 |
|---|---|
| 阶段输入输出、待完成与失败判定 | [contracts](references/contracts.md) |
| 旧规则、测试、交付包继承 | [historical-feature-inheritance](references/historical-feature-inheritance.md) |
| SH16 图族和专门入口 | [sh16-routing](references/sh16-routing.md) |
| 当前结果与从原始输入重建的区别 | [raw-source-reconstruction-delivery](references/raw-source-reconstruction-delivery.md) |
| 并行、缓存与原生任务重放 | [native-execution-performance](references/native-execution-performance.md) |
| 规则批次、发布闭环、状态/等待与收益核验 | [batch-execution-and-publication](references/batch-execution-and-publication.md) |
| HIL答复导入后的规则应用、重建、回归与发布 | [hil-feedback-closed-loop](references/hil-feedback-closed-loop.md)；`pipeline.py hil-feedback`，成功须有本轮应用/发布证明，不能停在接收回执 |
| 精确历史 case、修复脚本与反例 | [detailed-rule-index](references/detailed-rule-index.md) |

## 可执行入口与边界

以下命令路径以本 Skill 根目录为基准；先查看对应 `--help`，配置须绑定实际输入。

- `scripts/pipeline.py plan --config BATCH.json --output NEW`：固定任务、路由和实现锁，不执行全部提取。
- `scripts/pipeline.py validate --run RUN`：校验阶段契约；退出 0/2/1 分别为通过/待完成/失败。
- `scripts/pipeline.py actions search TEXT` / `explain COMMAND` / `feature FEATURE_ID`：精简检索全部正式/历史入口，默认最多10项；不先打印整个脚本或台账。
- `scripts/pipeline.py actions current-project --pointer POINTER`：从明确且有哈希的当前指针读取图、缺口、答复和验收状态；不按目录时间猜版本。
- `scripts/pipeline.py batch plan|run|start|status|wait --help`：固定依赖、执行阶段、记录失败、查询变化；日志落盘，执行器内部等待进程。
- `scripts/pipeline.py batch-release --help`：已有规则生产→正式发布→实际有效值回证的配方入口；SH16配方按声明范围运行，不能冒充原始CAD全链或专家验收。
- `scripts/verify_dependencies.py`：核对四 Skill 代码版本和建筑依赖副本。
- `scripts/feature_impact.py --changed PATH --run --output NEW.json`：按台账运行受影响测试；未知代码变更采用完整回退。
- `scripts/run_native_task_batch.py --manifest MANIFEST --output NEW --cores N --monitor`：并行独立任务，保留共享进程预算和隔离输出。

`plan` 会锁定根 SKILL、脚本与资产；当前不锁全部 references。文档版本由分发快照/ZIP 哈希另行绑定。指令变更后新建任务计划，保留旧计划和旧冻结包，不改旧锁冒充旧版。

每批固定源/代码/策略、适用对象、验证和发布依赖。已知规则先覆盖全体适用对象，缺证据/冲突保留具体原因。已答问题先查回灌状态；同类清楚实例不重问。批次无新证据且无缺口净减少时先定位阻塞机制，不重复同一分析。

常规返回只含状态、差异、失败项和证据路径。等待只在revision改变、完成或失败时回报；空输出不重启任务。成功产物仅在输入、实现、依赖和实际输出哈希一致时可复用，并明确标为缓存；损坏产物不能按旧通过标记放行。

## 交付与状态

SH16 当前以 08–10 平面局部图、11 轴测局部图、跨图融合三层保存；SH16 先打磨，LF20 后冻结回测。其他项目按实际图纸识别。

继续工作先读取项目最新权威清单，不把通用 Skill 中的历史数量当成当前完成状态。最终报告分别给出历史能力、局部正确性、映射/属性缺口、代码与分发一致性、原始输入复现、人工验收。

保留批注及源值。语义改变使相关确认失效；未知参数不填零，不靠删除待核对象降低数量。可运行查看器包不等于从原始输入完整重建包。
