# 把同范围量测接入轴测查看器

源级范围量测已通过独立重放后，执行 `refresh-reviewed-expression-group-metric-viewer --parent P --output NEW --proof native/reviewed-expression-metrics.json --templates T --port PORT`。随后用 `validate-reviewed-expression-group-metric-viewer --verify-output NEW` 对当前父图、源范围、实际显示入口与导出值独立重放。

正式接入重新执行完整当前父图回证和范围量测回证；逐一比较范围内每条轴测边的系统、楼层、起终点和原属性路径。局部拓扑一旦改变，原范围上下文不得继续使用。保留组件overlay的原父图哈希，不能把所有旧属性证明重绑定到新整图哈希。

11图每条相关边显示“共享范围已画平面源线合计”，同时说明共享总量未分摊、既有独立量测保持、省略连接内长未知。已有独立边长不因共享范围分配未知而退回未知。这不是该边自身的长度，更不是完整安装长。当前每边值不覆盖原管径、长度或继承链，内部节点身份仍未分配。

导出只增加范围ID、共享范围JSON和来源哈希三列。共享总量在JSON中带 `aggregation_key` 和 `count_once_per_scope_id_not_once_per_edge`；不得对每边重复出现的共享总量直接相加。真实逐边长度字段继续保持原值或未知。源图持有问题的另一个范围不进入本次显示。

保持所有旧列顺序、旧值、图和组件。语义显示改变后使用新bundle及审查身份，历史批注保留但不自动继承人工确认。完成实际页面与两系统全网CSV核对后，才可宣称在线接入；在线范围信息不能冒充逐边属性完成率提升。
