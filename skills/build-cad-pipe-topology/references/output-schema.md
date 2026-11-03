# 输出数据约定

## 节点表

`topology_nodes.csv` 每行一个节点，至少包含：

- `node_id`：稳定唯一标识；
- `node_type`：`physical_equipment`、`virtual_equipment` 或 `tee`；
- `label`：设备名称或节点显示名；
- `floor`、`system`；
- `x`、`y`；
- 来源块、标签或省略符句柄。

## 边主表

`edges.csv` 每行一条相邻节点边，至少包含：

- `edge_id`、`start_node_id`、`end_node_id`；
- `edge_type`：`tee_to_tee`、`tee_to_equipment`、`tee_to_virtual_equipment`；
- `system`、起终点楼层与坐标；
- `path_length`、原始路径或其序列化表示；
- 可选端口 ID；
- 按设备类型聚合的清单。

## 边设备逐实例表

`edge_device_instances.csv` 每行一个源实例：

- `device_name`、`equipment_type`、`type_code`；
- 原始坐标和用于归边的语义坐标；
- `source_kind`：块参照、炸开几何或语义恢复；
- `source_block_name`、顶层句柄；
- `edge_id`、`edge_distance`、`assignment_status`。

设备名称必须唯一；`assigned` 实例必须具有 `edge_id`。

## 边设备聚合表

`edge_equipment_by_type.csv` 按 `(edge_id, equipment_type)` 聚合：

- 起点、终点；
- 设备类型；
- `device_count`；
- 该类型下全部 `device_names`。

## 审计表

按实际规则输出：短毛刺裁剪、阀门/放气阀展示腿回折、管道上下叠跨越复联、省略符与虚拟端口、图示断口愈合、未归属设备和排除的详图实例。

`pipe_crossover_gap_bridges.csv` 每行记录一处跨越断口的两端点、交叉坐标、断开管道系统、被跨管道系统、断口长度和相交角。任何节点坐标均不得落在记录的交叉坐标容差内。

若图纸存在跨越跳弧，另输出 `pipe_crossover_arc_normalizations.csv`，至少包含：`source_entity_type`、`source_handle`、所属系统、弧端点、交叉坐标、被跨系统、原显示曲线长度、归一化直线长度、`normalization_status`。原弧几何保存在 `source_display_geometry`，但节点边路径和 `path_length` 使用归一化直线；不得输出上下标高推断。

## JSON 与报告

`graph_with_edges.json` 保存节点、边、路径和设备聚合；`edge_summary.json` 保存稳定验收指标。报告必须说明排除范围、恢复的炸开符号数量、未解决项和验证状态。

## 必检约束

1. 节点 ID、边 ID、设备名称均唯一。
2. 每条边的起终点均存在。
3. 每个已识别边设备恰好归属一次。
4. 聚合表数量等于逐实例表按边和类型的分组数量。
5. 图中节点、边和实例计数与 CSV/JSON 一致。
6. 每个跨越断口只复联断开的管道，交叉坐标不对应任何节点。
7. 每个跨越跳弧只归一化其所属管道；交叉坐标无节点，边长不采用显示弧长，弧线方向不产生标高属性。

## 双视图兼容字段

节点和边的既有字段保持不变。需要跨图结果时，另存独立记录，不把融合值写回局部拓扑：

- 局部拓扑检查状态、未解决范围，以及该层内容哈希。
- 设备、端口、立管、路径映射。映射必须同时有两侧标识和源证据，允许一对多与多对一。
- 管径直接值、继承链、变径冲突。未知管径为空，不用 0。
- 物理长度的来源视图、计算方法和完整性。水平长度来自平面图，竖向长度来自轴测图。
- 双视图差异分类与处置。差异记录不能覆盖另一侧拓扑。

局部连接变化后，相关映射、继承和融合必须重算。语义变化使相关人工确认失效，旧批注保留。
