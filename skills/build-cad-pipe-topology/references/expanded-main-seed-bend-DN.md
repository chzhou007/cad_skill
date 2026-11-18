# 原主管标注源域延伸之后，重用两臂弯头继承

主管标注经原 native owner 沿同一条原生LINE、当前真实三通直通臂延伸到另一条已建边后，该边的无标注竖段仍须交给原同路径弯头 owner。不能只尝试“目标是三通第三臂”而漏掉同一 attribute_path 中已证明的主管种子。先完成种子域延伸，再重算其下游弯头／属性依赖；已有物理拓扑不因此重建或改连。

`reconstruct-expanded-main-seed-bend-DN --manifest M --output NEW` 整批读取当前全部待定竖段。`validate-expanded-main-seed-bend-DN --verify-output NEW` 独立重放。manifest.inputs 固定 axis_source、axis_graph、routing、canonical_components、known_vertical_proof、expanded_seed_proof、parent_viewer_manifest、parent_provider。完整当前查看器的原生重放会重跑其标注父链和主管种子owner，比较精确原始产物；之后复用该已回证的固定种子字节，避免第二次重复同一原生子树。

适用种子必须由原主管成对／直接标注及源LINE域 owner 独立证明，不允许从已知支路倒灌给主管。检查实际modelspace LINE、原XYZ／系统、域包含和同一原attribute_path；所有同路径种子值一致后，复用原 chain_evidence 和 annotation_guard。原两臂、源Z、短口、真实第三臂、重线、新DN及F标注保护不放宽。原始源歧义仍保留，不从平面或房间负荷引入竖段值。源Z和轴测绘图长不换算实体长度，括号数字不用于长度推算。

源级通过后，用 `refresh-expanded-main-seed-bend-DN-viewer` 和对应 `validate-... --verify-output` 发布。保留当前组件overlay及其父图原字节／旧图哈希，只对原精确竖段增加独立DN记录。所有旧管径、长度、列序、组件、映射、批注保持。完整当前parent带组件增量时，不能把当前整图哈希直接写回所有旧属性证明；必须沿已有显式overlay验证原属性图域。

SH16当前42个剩余竖段中，E0521路径0段1可由11图TEXT14F6F／1522C的DN300、LINE14AB8延伸和1522A处两臂转角回证。另41段保留；三层其余36段的250／300范围冲突不受此结果影响。这里只新增竖段DN，不新增整边／水平取值、连接或长度。该例是现有读取器次序与组合的修复，不是新的几何识别算法。
