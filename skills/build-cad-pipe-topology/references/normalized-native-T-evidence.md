# 已执行的断口归一化，须被后续三通核验继承

触发：重建图已有真实三通，但跨图核验只看未经归一化的原始 LINE，报端点短缺口或误把 `source_insert_handle` 中的省略符当作接管证据。

先固定同一原 CAD、局部图及原始 `normalization_audit.json` 的哈希。用 `reconstruct-normalized-native-junctions` 批量发现原审计全部 applied 接点；它重放原有递归 LINE 提取、去重、旧短尾处理、弯头修剪、近接点归一化，要求完整审计与原记录一致。不是按截图或节点 ID 补线，也不扩大原 profile 阈值。

调用格式：`pipeline.py reconstruct-normalized-native-junctions --manifest 输入.json --output 新目录`；独立复验：`pipeline.py validate-normalized-native-junctions --verify-output 新目录`。manifest 的 `inputs` 包含 `source`、`graph`、`normalization_audit`，每项具有 `path` 和 `sha256`。

当前组合支持同系统、同 Z、原生 modelspace LINE 的已应用轴向延伸。对私有 LINE 语义视图再次运行原生三通核验器，原规则仍检查三条唯一射线及额外同系统接触。嵌套、曲线、代理或只有候选 pending 的缺口保留未解决；供回水几何相交不会因此连通。原始 DXF、图、设备、元件和 ID 不修改。

证据必须区分原始接触和归一化接触。归一化距离是绘图修复量，缺口的物理长度仍为未知，不能把归一化线用于原始 LINE 长度覆盖。没有审计的原生核验仍拒绝这个缺口；远处 DIM_SYMB 波浪符不是本地三通依据。

已确认范围但内部表达数量不同的双视图，用 `reconstruct-normalized-expression-scopes` / `validate-normalized-expression-scopes`。原范围 manifest 增加 `inputs.iso_normalization_audit`。入口保留原范围、边界、路径、专家答复及平面核验，再重核轴测范围全部三通。只消除有归一化证据的轴测错误；不得解除另一视图尚未证明的圆环连接、分配内部设备身份、按比例分长或填管径。

SH16 组合回证：T306 的 1556B 至 1552A 为原 profile 内 2.35484 绘图单位延伸，原上限 3；14E1C 的 4.37806 候选仍 pending。二层供水范围的 12F6D 平面连接是另一问题，不能用 T306 已通过来证明。

回归资产：`test_normalized_native_junction_evidence.py`、`test_normalized_reviewed_expression_scope.py`；同时运行原 `test_omission_marker_native_T_gap_guard.py`、原生三通及范围测试。历史测试和原核验实现保留原字节。
