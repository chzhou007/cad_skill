# 已答复的两阀省略表达：原生归属与当前查看器采用

适用于已证明为同一条命名外接管路、平面图一阀而轴测图两阀，并已收到针对两组供／回水源实体的明确省略答复。不能把元件数量不同自动视为省略。

## 原生和答复重放

`pipeline.py reconstruct-reviewed-fragment-detail-index --manifest M --output NEW`；独立复验 `validate-reviewed-fragment-detail-index --verify-output NEW`。

入口通过原 `rebuild_fragment_component_index.verify_output` 重放全部旧元件提取、法兰接触、命名路径及原生显示几何，再用共享答复接收重放核对归档题目、浏览器快照、Pair、源文件和图版本。只解除显式答复涉及的两条来源差异：同系统、同映射、同平面边、同新旧源阀句柄；原生旧阀归属也须独立成立。

保留两侧真实 profile：平面一球阀、轴测两球阀，其他元件须完全一致。不能改写成“两个 profile 一致”，不能接受部分答复、信息不足、第三只阀或其他仪表差异。原来已通过的元件及其他待核对象保持。平面省略阀的位置、缺失物理参数继续未知；不合并两图源实例、不创建虚构平面符号。

产物沿用 `native_fragment_component_index_v1` 的数据／叠层接口，新 `application_mode` 与类型化回执指向本次答复应用 owner，原回执和旧 profile 原样保留。

## 只替换一个可还原的叠层

从原属性父图重新运行 `fragment_component_index.build`，包含此前已采用和本次新确认的全部实例。要求新旧两种叠层都精确还原到同一完整父图；新图保留每个旧实例，只有声明的新实例及对应边的元件汇总变化。不能在现有叠层之上再叠一次，也不能丢失先前恢复的实例。

SH16 此轮：原父图1574实例，旧叠层1576，本次完整叠层1578；保留17813／17814，新增17816→E0047与17815→E0099。8个原生归属未解决对象不因本次答复而消失。

## 采用到实际当前查看器

`refresh-reviewed-fragment-detail-viewer --parent CURRENT --parent-provider CURRENT_PROVIDER --proof NEW_PROOF --output NEW --port PORT`；复验 `validate-reviewed-fragment-detail-viewer --verify-output NEW`。

父 provider 必须由父 bundle 的实际发布回执绑定，并与当前显示元件总数一致。不能因为原生映射核使用较早 provider，就撤回后来已发布的管径、长度或元件。共享原 `overlay`／`provider_from`，保留旧映射、成员、前沿和历史，替换既有叠层描述，保留原属性父图文件和全部属性上下文。

使用保持嵌套键顺序的 manifest 写入方式。前端按 `JSON.stringify` 导出证据，重排无关旧上下文键会改变 CSV 单元格。新组件不得改变任何既有管道属性导出值；元件导出只增加声明的实例。保留旧批注，更新 bundle 身份，相关人工确认不自动继承。

实际中文页面、供回水完整边表和元件表均须验证。SH16 本次应保持管径285、水平两项完整248／298及剩余50不变；元件660＋916增加为661＋917。源图回证、查看器采用和人工验收分别报告。

## 回归

`test_reviewed_fragment_detail_index.py` 检查显式答复、不同系统、旧阀原生归属、真实 profile、其他差异保护和整个父图还原。`test_refresh_reviewed_fragment_detail.py` 检查实际父发布身份、元件总数、旧映射／管径前沿和原历史守恒。原元件提取、负OCS、叠层与管径继承测试继续运行。
