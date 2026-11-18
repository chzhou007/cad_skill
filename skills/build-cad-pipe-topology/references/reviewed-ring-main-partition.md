# 立管分出的上下环管：按已确认分区复用原管径继承

适用于专家已明确给出主管两侧管径及原CAD范围，而源图用同一LINE穿过立管接入三通、导致上下标注互相传播的情况。房间或设备承担范围用于解释已确认分区，不据房间数量计算或猜测其他图纸的管径。

1. 保留原话、标注图、既有问题和Pair版本。`reviewed_ring_main_partition.py` 重新调用整层原生标注、F形标注、校准、源路径及当前三通读取器；旧已知管径须全部保持。
2. 用实际立管接入三通及其两个主管臂定义区段。范围必须源图连通、位于声明的对应侧、两端有原生三通证据，且候选管径来自当前冲突及专家明确答复。既有直接管径标注不能被覆盖。
3. 将已确认主管区段作为有来源的边界交给原继承核；继续复用其真实T、主支路、系统隔离和新标注停止规则。专家边界不是新增CAD文字，也不能产生虚构的变径点、管长或流向。新支路标注仍优先；未审范围不得出现意外管径变更。
4. 重放原／当前图局部星形、端口及源线，保持两个图版本分别可追溯。继承结果和原始冲突并存，不手改最终图。
5. `reapply_reviewed_ring_crossview_DN.py` 消费源阶段结果，重新执行原环路接入点发现、对应范围源路径／三通和设备支路检查。复用原映射ID及完整旧快照，不用管径选择对应。

**跨图ID边界：** 不同楼层的 `E0054` 等局部编号会重复。匹配至少绑定源图、图版本、楼层、系统及原对应范围；其他图纸同号边须明确排除。不能直接按源边编号搜索全部11图边并写值。

**取值边界：** 纯水平一对一主管可采用整边管径。混合边仅记录已对应的平面已绘支路管径；未证明时不分配到每个轴测水平子段，不赋整边／竖段管径。所有长度保持原值，缺失竖段长度留空。未知变径点不因管径分区确认而自动定位。

正式入口：

- `pipeline.py reconstruct-reviewed-ring-plan-DN --manifest M --output NEW`；对应校验命令 `validate-reviewed-ring-plan-DN --verify-output NEW`。
- `pipeline.py reconstruct-reviewed-ring-crossview-DN --manifest M --output NEW`；对应校验命令 `validate-reviewed-ring-crossview-DN --verify-output NEW`。
- `pipeline.py refresh-reviewed-ring-DN-viewer --parent OLD --output NEW --templates T --proof P --port PORT`；独立校验 `validate-reviewed-ring-DN-viewer --verify-output NEW`。

查看器新增有独立源证据的上下文和兼容导出字段。原图、元件、长度、批注和旧管径候选保持；已解决的有效未知／冲突状态更新，原批次字段继续作为历史来源。语义变更后的人工确认不自动继承。

后续批处理须通过 `refresh_reviewed_ring_partition_DN.effective` 读取 **app实际导入的属性入口**。保留的旧文件不能决定当前入口；否则会漏掉后来已采用的feature。发布前核对真实中文页面及供回水完整CSV，并将源级、当前发布和人工验收分别计数。
