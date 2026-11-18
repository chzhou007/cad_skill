# 原 CAD 重建输入、阶段归属与交付范围

## 区分验证入口和生产入口

查看器、属性读取器及其验证过程的输入闭包，不能直接当作原 CAD 完整重建输入集。完整生产入口还会读取批次／task 元数据、材料原型库、归一化配置、各阶段 policy map、专家原始答复与 Pair、校准控制和后续设备归属规则。

先对照原生产命令逐项检查输入是否进入分发包，再通过实际生产执行记录子进程的读取依赖。SH16 的一次复现中，查看器 corpus 包含源 DXF，却未包含 08–10 原生产命令直接使用的 68 份配置；仅补源图不能修复这种缺口。直接配置和即时引用的收集仍不是完整传递闭包，未知／缺失／临时产物及未观察子进程必须保留状态。

历史原始入口及其后续局部阶段须一起复现。基础 family 图一致，不代表最新的设备归属、断口、波浪主管或身份迁移已接入。比较完整节点／边／属性／元件记录，不能只比较总数；旧快照中已知错误也不能据此视为正确。

## 新任务必须绑定自己的父阶段

在新目录重建时，子阶段的 `parent_task_root`、父比较报告和父 receipt 仍可能指向旧任务。原 containment 检查应拒绝“新父图位于旧任务之外”，不得删除该检查或把读取旧报告当作新任务已验收。

1. 先实际重建父图及元件，核对源、代码、配置和已知行为。
2. 在新父目录生成其实际 receipt；源语义事实取自新产物。复用旧的已审查报告须证明图和原生事实仍逐项一致，并运行原源图对照校验。
3. 创建新的执行配置，仅重绑任务目录及新父报告／receipt 的哈希。保留原配置和证明；源、图、Pair、选择范围、阈值及元件约束不得随路径迁移而改变。
4. 用原子阶段入口继续重建，再执行原父阶段、源图、元件和完整性校验。新目录绑定不自动继承人工确认。

生成新任务的执行配置不等于全局改写历史证明中的路径。校准证据与本次生成产物分别标识；只有已证明等价的源范围才允许复用历史校准输入。

## 批处理运行及调度

需要保存 PNG 的无人值守原始重建，在导入绘图库前显式选择批处理渲染后端，例如 `MPLBACKEND=Agg`。查看器可运行的 Python 包不一定包含 Tk/Tcl；不能把缺少窗口后端误判为管线提取错误。后端调整后仍须核对原图、拓扑、元件和中文可读性，字体依赖也要记录。

独立楼层／图纸可并行；后续阶段以自身父产物及审计实际完成为启动条件。父图哈希、元件表和原生审计就绪后可启动该楼层后续阶段，不必等待其他图纸；同一输出目录不得并发写入。锁文件、计划或旧状态不证明进程仍存活，等待须核对实际进程句柄。

## 分开报告验收层次

分别记录：中文读取、原始入口执行、当前后续阶段、源图对照、跨图映射／属性融合、交付输入完整性、干净目录仅依赖分发输入的复现、实际查看器／CSV，以及 HIL。

在工作站原路径读取历史配置并成功重建，证明原算法及组合入口可运行；不证明输入包已独立完整。重新生成当前图也不自动修复原图歧义或增加未知管径／长度。技术结果复现、全图正确性和人工验收继续分别记账。

## 有界的历史路径输入适配

当历史 JSON／证明必须保留原路径时，可使用 `scripts/delivered_source_input_runtime.py PACKAGE WORK INDEX_SHA ENTRY [args]`，由包内 Python 加 `-I -X utf8 -B` 启动。它按已固定哈希的索引将历史读取转到交付文件，并记录每个 Python 子进程的读取；不是操作系统沙箱，也不替代原生产入口或原生对照校验。

索引包含 `files`（规范化历史路径到 `relative`、`sha256`）、`directories`、`negative`、`forbidden_historical_final_graph_hashes` 和 `adapter_sha256`。修改索引或适配代码须生成新的版本及哈希，原输入和证明不得改写。包目录与可写工作目录必须分开；新父图、执行配置、临时校验产物和日志放入工作目录。以外部历史最终图直接充当生产输入须阻断；参考比较在生产之外进行。

兼容处理须保留原库的语义：不存在的可选文件返回原生 `ENOENT`，目录项支持当前 Python 的 `is_junction` 等临时目录清理接口，系统空设备允许子进程丢弃输出；这些均不是放开外部文件写入。逻辑目录只能枚举索引中的成员，不能暴露其他物理别名。返回交付文件的真实 stat，不伪造历史 inode／时间来通过旧缓存。

包内模块目录的大小写和原生字体须明确绑定；预置绘图字体清单，使用 `Agg`，在几何重建前验证源图中文及实际中文渲染。Python 文件审计不覆盖所有 C 扩展读取，已知 Pillow／Matplotlib 字体入口另有路径适配；未知原生运行方式不能据此声称封闭。

执行成功还须检查所有根进程及子进程的 `access-receipts`，不能只看退出码；未收录读取不得被原库捕获后当作已完成。完整原始入口及其当前后续阶段分别比较图与元件表；语义和人工确认仍按原阶段处理。专项回归入口为 `scripts/test_delivered_source_input_runtime.py`；其通过不代替既有 CAD feature 回归。

不能只拦截 `subprocess.Popen`：Windows 的 `ProcessPoolExecutor` 通过 `multiprocessing.spawn` 启动工作进程，须在原生 spawn 命令边界绑定相同的包、工作目录、索引和适配代码，保留原工作函数及 spawn/prepare 协议。按启动 token 对照每个请求与工作进程 receipt，未观察的进程池不能当作已封闭。仅本进程标准 `pyc-<pid>-<counter>-<token>` 命名管道的 stat 探测归为 IPC 运行时资源；其他进程的管道及文件读取不因此放开。

多个并行阶段共用工作目录时，按实际根 PID 的后代进程和 spawn token 汇总，保留其他根的原始记录；整个目录的 receipt 数量不能替代进程归属。源进程结束与协调器落盘 receipt 之间可能存在短暂间隔，应重观测同一任务，不能因此重启已完成的重建。

## 从新父图实际执行跨图层

`generated_local_parents` 将旧逻辑路径绑定到工作目录中的新父图／元件表副本。每项记录 `relative`、`sha256`、`producer_receipt_relative`、`producer_receipt_sha256` 和 `producer_field`。当前支持的生产证明模式为 `raw_CAD_to_current_local_topology_delivered_API_input_replay_v1`，字段指针为 `["local_topologies", index, "graph" 或 "components"]`，并要求该记录的 `graph_and_component_bytes_exact` 为真。检查实际生成输出角色，禁止把 `reference_graph` 当作新产物。输入副本及证明在读取时复核哈希，保持只读；返回真实 stat，保留原始 JSON 路径和批注。

`historical_read_cwd` 只恢复索引已声明输入的原项目基准；新增输出使用工作目录的绝对路径。`entry_spellings` 保存原目录记录中的成员大小写，只允许相同 Windows 名称的大小写恢复。目录清单与原审计比较区分大小写，不得通过折叠审计键来放行差异。

映射生产入口还可能需要原生生产 manifest、其显式输入，以及答复接收器验证的完整 Pair／概览／向量资源。按固定定义及哈希补入，保留原接收器和媒体预检；查看器已能读取不代表这些生产依赖齐全。对源定义、专家答案、原图歧义和工程参数分别记账。

限定 Node 模式使用 `qualified_node_reader_bridge={relative,sha256}` 绑定 `scripts/delivered_node_read_bridge.py`。仅原有指纹合格的纯属性读取器可进入：保持原命令程序、JS、图及 manifest 字节，复制其完整相对模块闭包到工作目录，按原参数形态运行包内 Node，原桥接器再次核对输入。紧凑静态 `import{…}from'…'`、`export*from'…'`、普通写法和副作用导入都须跟踪；动态导入、外部模块与路径越界仍按原规则拒绝。跟踪桥接器代码与输入索引，不缓存属性结果，不放开任意 Node 调用。

完整原生入口需通过原 NumPy／绘图库安装位置检查。可用 `scripts/materialize_standard_python_role.py --package PACKAGE` 从已交付的 split runtime 生成独立标准布局，派生 `_pth` 文件；不修改输入运行库、不伪造 sysconfig。索引以 `packaged_runtime_role={relative,sha256}` 绑定其 `role-manifest.json`，解释器须与角色声明一致。原生校验、源图重算、实际属性读取和分发验证分别保留证据。

完整入口可能通过有界父阶段调用历史 Skill 中的纯属性读取器。此时用 `qualified_node_reader_roots` 显式列出其 `root`、`policy`、`sha256`、`mode`，policy 必须仍位于该根的 `orchestrate-cad-drawing-pipeline/assets` 且已在交付文件索引中固定。桥接器核对原 policy 哈希、原函数指纹及完整模块依赖后才执行；未声明的历史根、邻近根、变更 policy 和任意 Node 调用仍拒绝。紧凑导入识别由新接入层在此显式模式下安装，原有不可变读取器源码保持；不能为修复读取闭包而使历史父阶段的源码一致性检查失效。只验证当前根的独立读取不能证明历史父阶段已接通，须再运行完整父调用。

历史父阶段的派生依赖缓存必须使用自己的新工作区。`derived_cache_roots` 仅绑定固定 manifest 中 `parent_application.cache_root` 这一执行资源：每项含模式 `derived_cache_from_fixed_parent_application_v1`、工作区内 `relative`、原 manifest 路径及哈希。原缓存 owner 解析根目录后，查找缺失键、临时写入和原子替换均在新缓存进行；输入、证明和包含关系检查保持原样。不能把随新运行绑定产生的缓存键查找误记为固定源文件，也不能凭缓存缺失解除原生重放。越界或无固定 manifest 依据的缓存角色应拒绝。

新查看器目录的 Node 属性读取还会检查每层祖先目录的 `package.json`。在重算前用 `collect_execution_package_ancestors.extend(index, package, work)` 固定实际存在的配置和不存在的探针；既有文件变化、原先不存在的文件出现均须拒绝静默重绑定。新任务目录自身的祖先不能因旧查看器已通过而遗漏。先对目标目录的实际属性入口做读取预检，再启动完整原生产入口；不要等完成几何计算后才发现新的配置探针。

独立标准运行库还须恢复已交付 wheel 安装记录中的目录及模块名大小写。`materialize_standard_python_role` 读取 `.dist-info/RECORD`、核对存在文件的内容哈希及大小，先建立权威目录名，再复制原字节；保留原包和虚拟环境库的优先关系。`pil/image.py` 的字节存在不等于隔离模式能导入 `PIL.Image`。使用真实交付库在不安装输入适配器的进程中验证 NumPy、绘图库及中文绘图；玩具库测试或路径适配器下能导入，不能替代这个检查。

## 生产 API 结果与工作文件来源

成功读取列表不能覆盖失败探针和临时产物。可选 `producer_observation` 固定 `producer_input_observation.py` 的 `relative/sha256` 及 policy 的 `policy_relative/policy_sha256`。默认关闭，不改变原适配器的读取记录、CAD算法、stat或原缓存检查。

先使用 `producer_API_input_discovery_v1` 运行原生产命令，保存实际返回、异常类型与 errno、空路径探针、缺失文件、目录状态和原生审计尝试。审计事件发生在调用返回之前，只能记为 attempt，不能据此宣称写入成功。以这些实际记录固定追加文件、目录、负探针及启动前 owned_seeds，再用 `producer_API_input_enforcement_v1` 重放。发现模式正常退出不等于严格通过。

预置工作文件必须有固定来源哈希；不得把任意已有工作文件或历史最终图当作新产物。成功的 Python 写入与原子改名通过每进程追加日志提供来源，其他工作进程读取时重新查证该日志。未记录成功写入的审计尝试不授予生成产物身份。保留失败运行及未知文件，不能清空 unresolved 来发布。

逐进程 `producer-observation` 结果与原 `access-receipts` 一起核对根 PID、后代和 multiprocessing token；单进程严格通过不代表进程树闭合。原生 C 读取仍仅覆盖既有显式字体／资源入口，不声称操作系统隔离或一般原生I/O闭包。实际图与元件输出还须逐字段对照，不能以观察通过替代SH16拓扑正确性、完整原始分发或HIL。回归为 `test_producer_input_observation.py`，包含真实子进程安装后的原字节执行，不能只测未安装的包装函数。

将已结束的发现模式记录提升为严格约束时，复用共享入口 `pipeline.py build-producer-input-policy --producer-result RESULT --package PACKAGE --seed-manifest SEEDS --output NEW`，随后加 `--verify-output NEW` 独立重导出。它继承原项目脚本的合并逻辑，额外核对实际根进程、同一输入版本、各份记录哈希，以及生成时仍成立的文件／目录／缺失状态。不得混入其他批次记录；发现阶段已有输入变化或原适配器漏收读取时先诊断。

SEEDS 的 schema 为 `delivered_producer_startup_seed_bindings_v1`，每条提供工作区内 `relative`、交付包内 `source_relative`、`sha256` 和 `role`（runtime_cache_seed／execution_entry／execution_config）。只固定明确来源的启动种子；不能从最终工作目录的现有输出倒推其“初始输入”身份。输出 policy、derivation 和 receipt 各自保留来源，主流程仍须实际执行原生产入口和全部子进程，政策生成成功不等于生产重建通过。该共享入口本身不改变CAD规则或增加参数值；回归为 `test_build_producer_input_policy.py`。

长任务会遇到 Windows 重用 PID。`producer_process_identity` 使用实际 `pid + started_ns` 区分实例，并按原始父进程生命期、启动记录顺序及 multiprocessing token 核对关系；不能把同号的新进程当成重复记录或仍存活的旧进程。无时间信息的历史记录只在PID唯一时保留未知epoch，不补造时间；父生命期有歧义时明确拒绝确认。查实时状态须读取实际句柄的创建／退出时间：PID已分配给较晚进程时，原实例已结束；句柄查询被拒绝不等于原任务已结束。共享政策入口同时固定此身份模块哈希。回归 `test_producer_process_identity.py`，实际132进程案例包括4组PID重用。

Windows 的 shutil.copy2 可直接通过 CopyFile2 复制，不经过 Python open。观察器须在原 copy2 成功返回后记录实际目标文件及源路径，复制前核对固定来源和工作区写入边界；目录目标按真实返回的文件路径记账。仍调用原库复制字节和元数据，不伪造时间或成功，不把失败复制或已有未知文件记成新产物。限定入口不代表一般原生C I/O已覆盖；回归 test_producer_native_copy.py 包括真实安装后的复制、目录目标、失败返回、外部写入和未证明来源保护。

生产观察器与 generated_local_parents 组合时，qualified_fresh_parent 须继承原 Runtime 的实际产物角色；每次读取仍调用 checked_generated 核对内容与原生产证明，写入继续拒绝。不得把已证明的新父图误当作普通包外文件，也不得把历史同哈希副本变成启动种子。严格政策生成器按实际工作区和固定输入索引重新校验 local_topologies 的 graph／components 指针及证明哈希，单独记录 qualified_generated_parent_inputs，不加入 additional_files 或 owned_seeds；reference_graph、路径越界及证明变更仍拒绝。回归 test_observed_generated_parent_inputs.py。小范围8份父图读取通过只证明该组合入口，随后必须实际运行完整跨图生产及其进程树。

包目录迁移通过 pipeline.py project-producer-policy --source-policy POLICY --source-receipt RECEIPT --source-package OLD --target-package NEW --output FRESH 处理，只转换 additional_files、directories、negative 的物理命名空间；逐项核对原／新字节、目录实际成员和缺失状态。原索引、业务JSON、生产证明及 owned_seeds 相对绑定保持，不做全文字符串替换。正向输入不得位于原包之外，未支持的新约束字段必须拒绝；包外负探针保留并检查，不能据此声称跨用户配置已隔离。--verify-output 独立重算投影证据。投影本身不重导出原生产政策，也不证明新位置的生产执行；更换既有规范运行库后，须在新位置观察新增探针、固定种子来源及声明的启动缓存manifest，再运行严格入口。回归 test_project_producer_policy.py。
# Recursive native copying and generated-input provenance

If a generated `public/app.js` is held as `owned_read_without_seed_or_successful_writer`, check whether the producer used `shutil.copytree`. Its default `copy_function` captures the original `copy2` at import time. On Windows, that old function can invoke native CopyFile2 without returning through the observed `shutil.copy2` wrapper. Merely replacing the module attribute misses this path.

The shared observer routes only the captured original default through its existing successful-return copy owner. Preserve caller-supplied custom copy functions, recursive behavior, ignore handling, metadata and failure exceptions. A failed native/custom copy never grants generated-file ownership. Do not add the generated file as a trusted seed or relax the source gate. `test_producer_copytree_observation.py` reproduces the actual installed-runtime failure, verifies successful nested native copies and rejects failed custom copies. Run the original input/copy/receipt tests alongside it before another cold producer run. A local test pass does not prove whole cold reconstruction closure.

