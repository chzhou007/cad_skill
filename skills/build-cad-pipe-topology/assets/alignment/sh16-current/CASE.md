# SH16 CAD 管网拓扑对齐用例

该目录保存 `build-cad-pipe-topology` Skill 的版本 1 对齐基准。

从 Skill 根目录一键重跑并验证：

```powershell
python .\scripts\run_alignment.py
```

`manifest.json` 是机器可读的验收口径；`expected/outputs` 是人工比图与回归比较的期望产物。

版本 1.1 增加管道上下叠跨越规则：复联 2 处短断口，但交叉位置不生成节点。验收器会直接以 `pipe_crossover_gap_bridges.csv` 对照节点坐标。

当前图的供回水管层没有 `ARC` 或带 bulge 的多段线，因此“跳弧表示不相交”的规则属于未触发能力项，不改变本用例的节点、边和设备计数。

Current final baseline: v1.2.1-junction-fix, 427 nodes / 579 edges. Four recovered three-way junctions and source marker C19 supersede the old final counts; earlier-stage snapshots remain historical.
