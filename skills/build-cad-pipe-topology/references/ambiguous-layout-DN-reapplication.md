# 将有歧义的管径标注交给既有重复模板读取器

初步文字投影有歧义，不代表后续来源识别一定无法判定。旧入口只把已初步分配的标注交给 `native_repeated_branch_DN_layout`，会遗漏它原本擅长的拥挤标注。

`reapply_ambiguous_layout_DN.py` 对当前全部“投影歧义”待处理竖段重跑原投影和F优先规则，收集完整标注集合，再一起交给原重复模板读取器。保持至少四个独立源实例、相同模板／姿态／文字样式／有符号偏移、源Z、唯一当前管段及竞争管线检查。全部目标共同排除出对照样本，不能逐个重试后将其他未解决目标当训练样本。

定位到原始竖段后，用原 `owned_annotation_guard` 检查新管径及F屏障，再用原 `chain_evidence` 在同一源块、同一路径的真实两臂弯头间续传。初步歧义可以解除，真实变径、歧义源线、其他路径、省略接管长度不能因此跳过。无需重新判定系统颜色，不修改CAD或拓扑。

正式入口：`pipeline.py reconstruct-ambiguous-layout-DN --manifest M --output NEW`；独立回证：`validate-ambiguous-layout-DN --verify-output NEW`。在父级447段来源完整重放后，再核验本轮归属和续传。

查看器用 `refresh-ambiguous-layout-DN-viewer`／`validate-ambiguous-layout-DN-viewer`。沿用实际app导入的完整属性入口，扩展原竖段上下文，保留全部旧字段及值、原管径分区、平面属性、组件和批注。源级新增与真实中文UI／供回水CSV采用分别记录；不赋整边DN、不填未知长度，不继承人工验收。

SH16：15406／15407／15459／1545A的四个DN80归属由原识别器和168个独立控制标注重新验证；随后四个同接管竖段由原两臂规则续传。它们是既有规则的入口补齐，不是新建八根实体管。
