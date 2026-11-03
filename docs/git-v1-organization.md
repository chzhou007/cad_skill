# Git v1 梳理：以「轴测图完整生成」为核心 feature

> 目的：把本工作目录整理成可上传 git 的代码仓库，v1 只承诺一件事——**轴测图（isometric family）从源 DWG/DXF 到拓扑+查看器的完整生成**。其余图族（原理图/吊顶/室外/平面）代码保留但标注为实验性，不进 v1 验收。

## 1. 仓库定位

| 入库（git 跟踪） | 不入库（.gitignore 已排除） |
|---|---|
| skills 四件套（可执行流水线） | `output/` `work/` `archive/`（过程工作现场） |
| docs/ 契约与规范（小体积 md） | `releases/`（交付物 zip，263MB/包级，走归档或对象存储） |
| fixtures/ 回归基线（小 JSON/CSV） | `visualizer/.venv`、test-results、大 PNG |
| examples/ 运行配置样例（须去本机绝对路径） | 任何带本机路径/源哈希绑定的运行快照 |

原则：**git 放代码与契约，交付物和证据链放发布物**。历史发布包在 `releases/` 保持只读，不进仓库。

## 2. 建议仓库结构

```text
E:\codex\CAD\                  ← git root
├── README.md                  ← 重写为产品说明（现为工作日志，见 §7 草稿）
├── .gitignore                 ← 已生成
├── docs/
│   ├── git-v1-organization.md ← 本文档
│   ├── CAD-conversion-pipeline-v1.0.md
│   └── contracts/             ← 从 skill references 提炼的对外契约（可选）
├── skills/                    ← v1 冻结的四 Skill（装配方式见 §3）
│   ├── orchestrate-cad-drawing-pipeline/
│   ├── build-cad-pipe-topology/        ← 轴测引擎在此
│   ├── extract-cad-building-context/
│   └── visualize-cad-pipe-topology/
├── fixtures/
│   └── isometric-sh16-11/     ← 轴测回归基线（graph/edges/nodes CSV+JSON 摘要）
├── examples/
│   └── isometric-batch.json   ← 单任务轴测批配置样例
└── tests/ → 沿用各 skill scripts 内 test_*.py，不强制搬迁
```

## 3. 冻结哪一版代码（重要）

Skill 代码在本目录内存在多代快照，**直接整个目录推 git 会把历史版本一起带上**。建议装配方式：

1. **基准**：`output/CAD-skill-设备归并与源图对照-v2/skills/`（拓扑 1.14.0 / pipeline 1.1.1 / architecture 1.1.3 / viewer 2.9.1，最新且含 source_comparison 门禁）
2. **补齐**：该 overlay 包声明"历史 alignment 资产不重复打包"，需从 `packages/skill/cad-pipeline-v1.0.0/build-cad-pipe-topology/assets/regression/sh16-v17/` 并入回归资产
3. **收口**：修正 VERSION 文件与 SKILL.md 版本号不一致（v1.0.0 包内曾有 1.8.0/2.5.0 未同步问题）；`dependency-lock.json`/`version-lock.json` 以装配后的真实文件重新生成 SHA256
4. `packages/skill/cad-pipeline-v1.0.0` 与 log-update 包**不入 git**（已被 1.14 取代，属历史物）；如需留档放 releases。

## 4. 核心 feature 规格：轴测图完整生成

**定义**：输入轴测 DWG/DXF（暖通空调水系统轴测图，含设备、炸开元件、三射线 T 节点、省略符），输出完整拓扑与可交互查看器，全程源句柄可溯源、ID 可映射、回归可复现。

**引擎构成**（`build-cad-pipe-topology`）：

| 模块 | 职责 |
|---|---|
| `build_isometric_v17.py` | 轴测适配器：稳定设备归属（拒新绑定越界）、肘部过冲修剪、近接点吸附、id_mapping 生成 |
| `legacy_v17/analyze_graph.py` | 管段收集、系统图层、几何容差 |
| `legacy_v17/build_edges.py` | 节点/边构建主流程（含 provisional matches） |
| `legacy_v17/connect_equipment.py` | 设备管口连边 |
| `legacy_v17/place_equipment_nodes.py` | 设备节点放置 |
| 共享模块 | `pipe_geometry` `topology_normalization` `equipment_assemblies` `instrumentation` `exploded_templates` `source_glyphs` `normalize_cad_geometry` `native_inline_anchors/coordinates` |

**流水线链路**：`pipeline.py plan`（family=isometric）→ parameters → topology（isometric 引擎）→ visualization（viewer 生成）→ source_comparison（1.14 门禁）→ validate（退出码 0/2/1）。

**输出契约**（每任务）：`topology_nodes.csv`、`edges.csv`、`graph_with_edges.json`（含 path_points/attribute_paths）、`edge_device_instances.csv`、`virtual_equipment_nodes/ports.csv`、`id_mapping.json`、`normalization_audit.json`、viewer 目录（含 validation-report）。

## 5. v1 验收指标（发布门禁，全过才打 tag）

1. **回归基准**：SH16-11（`11-空调水系统图.dxf`，sha256 `46e14185…fcd677b`）重建结果与 v3.7.2.1 基线逐句柄一致：**424 节点 / 576 边 / 302 T / 1560 组件**；`id_mapping.json` 对旧 ID 映射率 100%
2. **完整生成空跑**：从 examples 配置一键 plan→topology→viewer，`validate` 退出码 0；viewer 打开后计数与 graph.json 一致、无隐身节点（PENDING 筛选校验）
3. **测试全绿**：轴测链路测试（`test_pipe_geometry`、`test_near_junctions`、`test_equipment_assemblies`、`test_instrumentation`、`test_exploded_templates`、`test_native_inline_coordinates`、`test_topology_normalization`、`test_pipeline` 等）100% 通过
4. **守恒**：源实体去向账 100%（含"保留原样"）；normalization_audit 逐条有记录
5. **诚实边界**：文档明示——长度为绘图单位、管径/阻力系数不臆造、流向未验证；不宣称水力正确

## 6. 执行清单（按序）

- [x] `.gitignore` 生成（排除 output/work/releases/archive/zip/大图/venv）
- [ ] 装配 `skills/`（§3 的 1.14 基准 + assets 补齐 + VERSION 修复）到仓库结构
- [ ] 提炼 `examples/isometric-batch.json`（去本机绝对路径，改相对/占位符）
- [ ] 从 v3.7.2.1 的 SH16-11 `topology/` 提取 fixtures 基线（CSV+摘要 JSON，约 1MB 级，入库）
- [ ] 重写 README（§7 草稿）
- [ ] 本地跑 §5 验收 → 打 tag `v1.0.0-isometric`
- [ ] 决定远端（GitHub/内部 GitLab）与大文件策略（releases 不入库，另挂归档）

## 7. README 草稿结构

```markdown
# CAD Pipe Topology Pipeline
从暖通 CAD 图纸提取管网拓扑的可复现流水线（四 Skill：总控/拓扑/建筑/可视化）。
## v1.0.0 — 核心：轴测图完整生成
能力边界、输入输出契约、快速开始（plan/validate 命令）、回归基准（SH16-11）。
## 图族支持状态
isometric ✅ v1 验收 | schematic/ceiling/outdoor/plan ⚠️ 实验性 | 材料表/建筑辅助 ✅（不伪造拓扑）
## 原则
证据不足保留 pending；不臆造管径/阻力/流向；产物溯源到源句柄。
```

## 8. 版本路线（预告，不进 v1 承诺）

- v1.1：source_comparison 门禁全流程 + fixtures 扩到多图
- v1.2：schematic / ceiling 图族转正（对齐 A 楼 03 已验证规则）
- v2.0：跨图计算总网 + 供回水绑定消解（依赖 SH16 待核项攻坚）
