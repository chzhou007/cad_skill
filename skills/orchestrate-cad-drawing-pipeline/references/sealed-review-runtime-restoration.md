# 固定输入包的独立运行验收

适用于已有严格输入闭包和内容寻址 corpus 的查看器交付。入口为
`scripts/restore_sealed_review_runtime.py --corpus CORPUS --output NEW --manifest-sha256 SHA --binding-sha256 SHA`。
两项 SHA 取自可信的固定输入回执；输出必须是新目录。

- 从 corpus blobs 恢复 Python、Node、site-packages、固定 Skill 和当前查看器；不读取本机源码来补文件。
- observer 的路径可能小写归一化。恢复文件名时，必须使用同一哈希绑定的 runtime-binding 中原始大小写。`ElementTree.py`、`PIL`、含 `DN` 的 Python 模块不能仅按小写逻辑键落盘。
- `_pth` 仅允许包内标准库、依赖和 viewer。使用隔离模式，并以无效 PYTHONHOME/PYTHONPATH 验证包内导入；原服务的同目录模块需要显式包内路径。
- 用随包 Python/Node 执行原 `refresh_reviewed_ring_partition_DN.effective`，由实际 app.js 选择属性 facade；逐边逐字段比较交付期望值。不能只比较总数或直接复制期望 JSON 作为计算结果。
- 启动原 serve.py，实际检查中文、供回水各自网络 CSV、元件实例和源图。`--open` 交给服务在绑定端口后执行，避免浏览器先于服务启动。包内 diagnose.cmd 校验内容并保存诊断。
- 包内原图、拓扑、元件、历史证明及属性代码保持字节一致；不改写历史绝对路径以绕过原验收。现有目标目录拒绝覆盖，批注目录保留可写；固定输入中没有批注文件时明确记录，不声称已迁移外部审查历史。

此入口只证明随包运行环境、有效属性重算和查看器可独立工作。**不能替代从原 CAD 开始的完整重建**，不能消除原图歧义或继承人工确认。原始 CAD 重建、跨项目回测、完整分发及 HIL 分别保留状态。

回归：`test_restore_sealed_review_runtime.py`；另需真实 corpus 恢复、包内二进制执行及实际浏览器／下载验证。保留失败尝试与日志，不覆盖历史回执。
