# 统一环管分区答复：允许候选，由当地原生标注选择

适用于专家已统一确认“两立管之间，上半环 DN200／DN250，下半环 DN300”，而各图当前标注给出不同上半环值的批处理。房间承担关系解释分区，不用于计算管径。不要把 `200/250DN` 当成单值 250；原单值解析器只适用于原单值答复，继续保留。

## 平面阶段

`pipeline.py reconstruct-alternative-ring-plan-DN --manifest M --output NEW`，独立复验 `validate-alternative-ring-plan-DN --verify-output NEW`。

manifest 固定原始整层 DN 结果、其回执和 manifest、原 CAD、局部图、当前三通配置、统一答复及原问题 Pair。以各立管接入点的已证明真实 T 和两个 through 臂定义上下范围。重读全层原标注、F 形标注、源路径、三通和继承；不读取轴测 DN 来消解平面冲突。

每条待补主管的原始标注继承候选与专家允许集合须只有一个交集；多个候选仍冲突，不能按顺序、距离或房间数量挑值。上下分区不能越过已声明边界，供回水分别处理。已经直接标 DN300 的下臂可以作为已知边界保留，无需重复生成“新标注”；已有已知值仍全部守恒。

给原推理核加入的是带来源的专家分区边界，不是伪造的 CAD TEXT、流向、实体变径件或实际长度。支路 DN 沿原规则继承，新支路标注仍优先。未审范围不得改变。源图、节点、边和 ID 保持；已有真实 T 已将两侧分为不同边，不能把上下主管再次归成一条同管径边。

## 跨图和采用

`reconstruct-candidate-ring-crossview-DN` / `validate-candidate-ring-crossview-DN` 复用已有对应，按源图、图版本、楼层、系统、两个独立端点及完整原生路径复核，不用新 DN 选对应。

当前 provider 的 `inputs.parent_provider` 可能仍保留较早来源元数据，不能据此认定它就是后来节点对应的生产者。应找到实际生成当前对应集合的原 owner；SH16 本批使用完整 complementary-chain owner。该 owner 继续通过既有冻结入口重放其原始前驱，原运行版本校验不放宽。要求本批对应观察仍来自这个已重放集合，其他后来新增的独立观察保留。

还要继承已有元件显示叠层：实际 `graph.json` 可因已核验球阀实例而与属性上下文的原图哈希不同。用既有 `fragment_component_index.restore` 和原叠层描述，证明整个图精确还原到已固定的属性父图；同时绑定实际显示图和属性父图。不能直接改旧上下文哈希，不能撤销此前元件恢复，也不能只比较几条目标边就宣称整个图还原。

仅纯水平、一对一、两端已对应的主管进入本批轴测整边 DN。平面短支路有可靠 DN 而尚无独立跨图对应时单列，不推定设备身份。普通相似边号在不同楼层必须排除。竖向和混合域不在本批赋整边管径，所有长度维持原值。

`refresh-candidate-ring-DN-viewer` / `validate-candidate-ring-DN-viewer` 从 app 实际导入的完整属性入口继续叠加；复用原已核验 ring-DN 前端守卫和差异守卫。旧分区上下文、旧 CSV 字段、旧数值、元件和批注保持。新字段使用独立 `candidate_ring_partition_*` 前缀，不能覆盖早先二层的分区证据。更新 bundle 身份，不自动继承相关人工确认。

## 回归资产

- `test_reviewed_ring_partition_candidates.py`：多值解析、原生唯一选择、直接下臂、旋转镜像、新支路标注、错误侧及未审范围。
- `test_reapply_candidate_ring_crossview_DN.py`：两个独立端点、方向反转及跨楼层同号边保护。
- `test_candidate_ring_DN.mjs`、`test_refresh_candidate_ring_DN.py`：原前端守卫、既有已知 DN、CSV 前缀、长度、竖向及历史分区信息守恒。
- 原单值 ring partition、映射和发布测试继续运行，不改写旧测试来适配新行为。

SH16 回证按“平面源级新值、已有映射重核、实际页面／导出采用、人工验收”分别报告；登记能力或测试文件数量不等于完成的管道数量。
