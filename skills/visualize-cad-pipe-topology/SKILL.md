---
name: visualize-cad-pipe-topology
description: Generate a runnable, portable CAD piping topology viewer and ZIP from completed node-edge results, component audits and source DXF/legend files. Use after CAD graph conversion or when the user requests interactive pipe highlighting, connected-equipment inspection, source-CAD comparison or a reusable visualization package. Supports local exception annotations, whole-dataset human review and portable expert pairs. This skill visualizes existing topology; it does not infer a new graph from screenshots.
---

# CAD 拓扑查看、专家对照与离线交付

Current release: **v2.11.20 HIL**

消费已有拓扑及属性，不从截图推断新连接。全流程见 [总控说明](../orchestrate-cad-drawing-pipeline/references/end-to-end-pipeline.md)。HIL答复使用[可执行回灌闭环](../orchestrate-cad-drawing-pipeline/references/hil-feedback-closed-loop.md)；主详图度量同义回灌使用 `scripts/reapply_reviewed_detail_feedback.py`，独立验证当前读取链，保留后续feature及批注，不能回退旧查看器。

## 执行顺序

1. 核对输入图、设备/元件审计、原图 DXF/图例、源哈希和阶段收据；中文可读、坐标一致。
2. 用正式构建/发布入口生成查看器；保留 WCS、源实体、设备/端口及属性出处，不自行归并图语义。
3. 原 CAD 与当前拓扑做大范围定位和局部 Pair 对照；确定性缺陷返回拓扑阶段修复。
4. 检查真正生效的属性读取链、页面和 CSV/JSON；候选与已发布值分开。
5. 剩余冲突进入集中专家页；问题高亮、边/节点定位和已答历史可追溯。
6. 验证编辑、保存、刷新、导出/恢复、Pair 与全网导出，再解压验证便携包。

## 显示和属性契约

- 沿用局部图及跨图结果身份，保持原始设备、边上元件、参数来源和原 CAD 证据。
- 统一 `pipe_attributes.horizontal` / `.vertical`：各自 DN、长度、适用性、状态、来源及分段范围；未知方向单列，人工整边值单列，不能隐式均分。
- 部分长度、XY中心线、共享范围长度、完整敷设长度明确区分；显示未知而非零。图片虚线连接不计入实长。
- 可疑边有原因标签、选择高亮和属性入口；源观察、计算结果、人工值分别保留，实际有效值和导出一致。
- 原生元件、设备和省略符保持源位置。未确认远端边界不显示成确定设备端口；回退符号位置标为未核实。

## 对照与专家打标

- 给整图/大范围原 CAD 定位，标出问题区域，再给相同范围/尺度的原图与拓扑 Pair；不能只给无上下文小切片。
- 交互视图与 Pair 共用 `public/native-rendering.js`。Pair 包含其裁剪范围内相关原生设备、元件和边界符号，不因当前叠加开关遗漏。
- 技术检查不等于人工验收。新图身份或语义变更不能继承旧确认；原批注和专家解释独立保留。
- 已答问题按问题和源版本去重；答复进入可复用规则/配置并批量回灌，不只改显示层。

## 编辑、备份与启动必须验证

1. 水平/垂直/整边 DN、整边长度和中文备注可编辑；保存后刷新重开仍在，失败时保留未保存输入。当前人工长度不按方向分摊。
2. 完整备份恢复问题、人工 DN/长度、备注与历史；检查数据集/基线版本，原子写入；不自动继承整图确认。
3. 同版包不同解压目录独立保存 `annotations`，服务按目录身份隔离；不能误复用其他文件夹的进程。
4. 完整解压到可写目录，核查运行环境、`diagnose.cmd`、`start.cmd` 和 `startup-logs`；启动失败先查日志和环境，不猜内存不足。
5. 用隔离副本实际测试保存/刷新/备份恢复、错误标记、Pair ZIP、节点边全网导出；回交包不得混入 QA 批注。

## 按需读取

| 任务 | 参考 |
|---|---|
| 水平/垂直统一属性与有效值 | [directional-pipe-attributes](references/directional-pipe-attributes.md) |
| 人工 DN/长度/备注、完整恢复与目录隔离 | [edge-review-and-manual-length](references/edge-review-and-manual-length.md) |
| 当前发布结果、离线包及保留原始重建边界 | [published-current-review-delivery](references/published-current-review-delivery.md) |
| 源表达与派生计算视图 | [calculation-views-v25](references/calculation-views-v25.md) |
| 全部构建参数、启动诊断、回归与历史 case | [detailed-rule-index](references/detailed-rule-index.md) |

## 入口与发布判定

从 `scripts/build_visualization.py` 构建；已有包按专题用对应升级/发布入口。统一方向属性用 `scripts/enable_directional_pipe_attributes.py`；编辑器和离线安全用 `scripts/upgrade_edge_attribute_editor.py`、`scripts/upgrade_offline_review_safety.py`；当前结果打包用 `scripts/package_current_review.py`。先看 `--help` 和对应参考，不把命令名单当成自动全流程。

按改动运行 HIL 后端/前端、Pair 渲染及数据门槛测试，并检查实际运行包。声明分别限定于静态检查、本机运行、原始输入复现及专家验收；未知专家电脑环境不写成已验证。历史详细规则见 [完整索引](references/detailed-rule-index.md)。
