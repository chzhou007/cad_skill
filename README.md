# CAD Pipe Topology Pipeline

从暖通 CAD 图纸（DWG/DXF）提取管网拓扑的可复现流水线，以四个 Skill 交付：

| Skill | 版本 | 职责 |
|---|---|---|
| `skills/orchestrate-cad-drawing-pipeline` | 1.1.1 | 总控：分流、任务隔离、契约校验、交付 |
| `skills/build-cad-pipe-topology` | 1.14.0 | 图族引擎：设备/材料识别、管路归一化、节点边与组件 |
| `skills/extract-cad-building-context` | 1.1.3 | 建筑上下文 sidecar（独立产物，不改图数据） |
| `skills/visualize-cad-pipe-topology` | 2.9.1 HIL | 交互查看器、HIL 人工审核、专家 Pair |

## v1.0.0 — 核心 feature：轴测图完整生成

输入暖通空调水系统**轴测图**（含设备、炸开元件、三射线 T 节点、省略符），输出完整拓扑与可交互查看器：

- 引擎：`build_isometric_v17.py` 适配器 + `legacy_v17/`（几何分析/构边/设备连边/节点放置）+ 共享归一化模块
- 链路：`pipeline.py plan`（family=isometric）→ parameters → topology → visualization → validate（退出码 0=完成 / 2=待定 / 1=失败）
- 产物：`topology_nodes.csv`、`edges.csv`、`graph_with_edges.json`、`edge_device_instances.csv`、`id_mapping.json`、viewer 目录

**回归基准**：SH16-11 轴测图（`fixtures/isometric-sh16-11/`）＝ 424 节点 / 576 边 / 302 T / 1560 组件，ID 映射率 100%。

## 快速开始

```powershell
# 校验依赖与文件哈希锁
python ./skills/orchestrate-cad-drawing-pipeline/scripts/verify_dependencies.py

# 规划一批任务（示例配置见 examples/isometric-batch.json，替换源路径后使用）
python ./skills/orchestrate-cad-drawing-pipeline/scripts/pipeline.py plan --config ./examples/isometric-batch.json --output ./my-run

# 校验产物契约
python ./skills/orchestrate-cad-drawing-pipeline/scripts/pipeline.py validate --run ./my-run
```

要求：Python 3 + ezdxf（拓扑构建）；查看器为无构建纯静态前端，本地起服务即可。

## 图族支持状态

| 图族 | 状态 |
|---|---|
| isometric（轴测） | ✅ v1 验收 |
| plant_schematic / ceiling_plan / outdoor_plan / plan | ⚠️ 引擎可用，实验性 |
| schedule（材料表）/ architectural_support | ✅ 只做参数/建筑提取，不伪造节点边 |

## 原则与边界

- 证据不足一律保留 `pending`，不强制匹配、不臆造连接
- 不臆造管径、阻力系数、流向；长度为绘图单位，非实测管长
- 每个产物可溯源到源句柄/源哈希；一产物只允许一个写入阶段
- 校验退出码 0 仅表示产物契约完整，不代表物理图正确或专家已确认

## 仓库结构

```text
skills/      四 Skill（v1 冻结代码）
examples/    运行配置样例（占位源路径）
fixtures/    回归基线（SH16-11 轴测）
docs/        设计规范与组织说明（含历史 README 留档）
```

交付物与历史发布包不入 git（见 `docs/git-v1-organization.md`）。
