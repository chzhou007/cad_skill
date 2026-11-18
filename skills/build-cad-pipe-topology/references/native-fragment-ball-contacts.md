# 原生局部管段上的球阀接触归属

整边含省略符拼接或设备展开表达时，不能把整边类别当作局部阀件的排除条件。先独立重跑原完整球阀清单及全部轴测管段来源路由，再将唯一 modelspace LINE 覆盖的原局部片段交给原 `footprint`／`source_owners` 双法兰接触规则。

私有投影只用于局部元件归属：原图、整边连接类别、所有 attribute_paths、供回水和设备语义保持不变。原有限 LINE 必须完整覆盖当前片段，路由的源句柄、图层和端点须与实体一致；全部原生管线和全部已证片段均参与竞争。法兰接触仍在原 WCS／Z 及原容差下检查。重复来源、多个片段竞争、外来 Z、缺失源证据及已有归属冲突均不自动采用。旧设备归属不作为物理接管证明。

`pipeline.py reconstruct-native-fragment-ball-contacts --manifest MANIFEST --output NEW_DIRECTORY` 生成独立源级清单；`validate-native-fragment-ball-contacts --verify-output NEW_DIRECTORY` 重新读取原始输入并验证。manifest.inputs 固定 source、graph、original_inventory 和 routing 四个 path／sha256；后两者须分别为原球阀归属和完整管段路由的正式输出，验证同时消费其回执和依赖。

所有旧元件行原样保留。已归属且相同的元件仅增加独立回证；未归属的原 INSERT 在唯一局部归属证明后才增加新元件，未知阻力和长度不填零。源级恢复不等于查看器已采用；后续须重验受影响跨图元件序列、发布索引、实际导出，并使相关人工验收失效。整边连通性、跨图对应、管径和长度均不由本规则新增。

回归覆盖旋转、镜像、负 OCS、交叉管、同源重复、重复图段、外来 Z、过期或不完整路由、已有冲突和幂等性。SH16 的未建图详图符号保持未归属，不能按距离或相似实例强制挂边。
