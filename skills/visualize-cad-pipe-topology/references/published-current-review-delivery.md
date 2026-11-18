# 当前图结果的独立审查包

适用于已完成原生生成和实际浏览器验证的当前查看器。先固定当前发布目录、已验证的标准 Python role、原图、专家答复及发布证明，再用 `package-current-review --binding M --binding-sha256 SHA --output NEW` 生成新目录和 ZIP。可使用 `--workers` 并行复制及校验文件；不重新运行未变化的 CAD 内核。

binding 使用 `published_current_review_binding_v1`，包含 viewer/runtime 的完整相对路径、SHA256、字节数，批注快照，固定端口和中文使用说明。extras 只使用 sources、evidence、skills 三个显式命名空间。历史绝对证据引用原样保留，通过附加清单给出当前随包原图，不改写旧证明或冒称离线重新计算这些外部引用。

- 复用原 `serve.py`、`hil_server.py`、`launch_review.py` 和全部发布数据。新启动层只加入已校验的包内 viewer 路径，解决隔离 Python 不搜索脚本目录的问题；不修改原服务。
- 使用已通过独立 ABI 验证的 package-only 标准 Python role，不借用本机 Python、Node 或全局 site-packages。先实际运行 `diagnose.cmd` 和 `start.cmd --check-only`，再在另一解压路径启动原服务验证源图、中文与网络导出。
- 校验不可变文件，保留 annotations 的原始历史并允许后续批注写入；startup-logs 保留当前机器的真实诊断，不把旧机器日志作为本次启动成功证据。包内运行时不接受额外未登记模块。
- 源文件变更、批注快照变化、路径逃逸或已有目标均拒绝发布。校验失败保留明确的 building 目录，不用局部产物替代最终包。

这是**当前结果审查包**，不是原始 CAD 全流程重建包。原始生产输入闭包、SH16 全图正确性、LF20 完整回测和人工验收分别记录，不因 ZIP 可启动而通过。回归入口 `test_package_current_review.py`；实际分发还需解压、随包运行环境与真实浏览器／CSV验证。
