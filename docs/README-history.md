# 最新检查交付：SH16 v3.6 Native Coordinate Repair

[完整交付包](releases/SH16-all-tasks-v3.6-native-coordinate-repair.zip) · [修复结果与未完成项](releases/SH16-all-tasks-v3.6-native-coordinate-repair/reports/native-coordinate-repair/README.md) · 总览 http://127.0.0.1:9580/ 。本轮恢复60个已识别阀门的边归属（08+24、09+20、10+16），节点边和源路径不变。物理设备接管/跨图映射及阻力参数仍待核，不宣称全部修复。转换Skill当前1.11.1，其他分别为总控1.0.0、可视化2.8.0 HIL、建筑1.1.0。旧发布物及服务保留。

以下为历史发布记录。

# CAD 工作目录

当前交付：**SH16 v3.5 Building Context**，[完整包](releases/SH16-all-tasks-v3.5-building-context.zip)、[本轮说明与调研](releases/SH16-all-tasks-v3.5-building-context/reports/building-context/README.md)，总览 http://127.0.0.1:9480/ 。06/07/08建筑上下文补齐并同步09/10；管网图数据未改动。该发布物内Skill保持原版本；本机最新Skill已升级为总控v1.0.0、转换v1.11.0、可视化v2.8.0 HIL、建筑上下文v1.1.0。各任务审核独立。

最新Skill统一包：[CAD Pipeline v1.0.0](packages/skill/cad-pipeline-v1.0.0.zip)，[流程、版本和使用说明](docs/CAD-conversion-pipeline-v1.0.md)。固定骨架、多标签分流；本轮仅更新Skill与契约，未重建上述发布物或继承审核确认。

## 历史工作记录

以下“当前”等字样均为当时记录，历史发布物及服务保留；本轮入口以上方v3.5为准。

# CAD 工作目录

设备/材料参数前置层：[参数梳理说明](output/SH16-equipment-parameters-v1/参数梳理说明.md)，目录 http://127.0.0.1:8779/parameters/（独立目录服务 http://127.0.0.1:8780/）。已建立设备性能、材料规格、原生图样、字段字典及任务内参数引用；未明确的规格/单位保持待核查，既有拓扑与人工审核不变。双 skill 已加入先建参数基础层、再提取拓扑的约束。

单图任务版：[任务说明](output/SH16-11tasks-v1/任务说明.md)。11 张图各自拥有 task ID、拓扑输出及审核范围；总览 http://127.0.0.1:8779/，第 11 张独立 viewer http://127.0.0.1:8778/。当前已就绪 1 张，其余图按各自任务状态继续；不跨任务合并或确认。双 skill 已加入任务隔离约束。

新任务（11 张 DWG，2026-10-20）：[处理说明](output/SH16-11drawings-v1/处理说明.md)。第 11 张已重新转化并生成 HIL；另外 7 张管网图待图族适配，其余 3 张为材料表/辅助图。逐图状态见 output/SH16-11drawings-v1/drawing-status.csv，独立服务 http://127.0.0.1:8777/，全部图纸状态入口 http://127.0.0.1:8777/drawings/。本批次不替换下方正式发布基线。

当前正式发布：**SH16 v1.3.0-HIL**；图基线 **v1.2.1-junction-fix**，427 节点 / 579 边 / 1560 部件。

- [当前发布说明](releases/SH16-v1.3.0-HIL/README.md)：HIL 独立可视化、完整交付、最终双 Skill、pair 示例和校验清单。
- releases/SH16-v1.3.0-HIL/SH16-complete-delivery-v1.3.0-HIL/topology/：最终节点边和审计数据。
- output/sh16-hil-v1.3.0/：当前 HIL 本机运行目录，http://127.0.0.1:8776/；标注自动保存在其 annotations/。
- releases/SH16-v1.2.1/：上一版，原始发布物保留。
- output/sh16-junction-fix-viewer/：保留的上一版运行目录，8773 服务未主动关闭。
- work/hil-v2/：HIL 开发、测试、安装前备份及演示证据，不作为正式发布入口。
- archive/2026-10-20/output/：早期效果图、旧包与回归结果。
- packages/：收到的原始 CAD 案例和 Skill 输入包。
- visualizer/：早期应用及 Python 环境，当前服务借用其中 Python。
- docs/：多中心 Pipeline 与门控讨论规范，HIL 实际交付以当前发布说明为准。

已安装 Skill 位于 C:/Users/lenovo/.codex/skills/：可视化 skill v2 HIL；转化 skill 更新 HIL 交付流程，提取代码及 SH16 案例仍为 v1.2.1-junction-fix。新生成的 viewer 默认含 HIL。安装前备份位于 work/hil-v2/pre-hil-skills.zip。
