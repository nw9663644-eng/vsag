# Lite 8bit RaBitQ 设计与交付边界

状态（2026-10-09）：按个人开发分支 `bcaf9c31e89abe811de84ffad3e1f63dadaa6882` 的真实实现核对。公开候选接口已经接通；性能验收和上游正式合入尚未完成。本文替代早期 RABITQ 枚举、VSAGLT01 v4 的提案，不代表导师或维护者已批准候选格式。

## 已定设计

| 项目 | 首次交付的选择 |
| --- | --- |
| 接入 | 非空 BruteForce 显式调用 BuildGraph(VectorStorage::RABITQ8, max_degree, ef_search)；ENABLE_RABITQ_LITE_BACKEND 默认 OFF，使用时开启 |
| 算法 | 平方 L2 估计；3bit 过滤 + 5bit 补充；4轮变换、6轮坐标调整、error rate 1.9、训练 seed 47 |
| 模型 | 一个固定质心与翻转模型，存编码和外部 ID；不在线重训，不常驻原始 FP32 向量 |
| 查询 | 沿用 Search、外部 ID 过滤，并支持 SearchWithOptions 单次预算；不支持并发调用 |
| 增删改 | 预备编码与局部回滚日志；验证后完整编码相同则不改图 |
| 持久化 | 保留独立 VSAGLQ01 v1 候选格式；不混用 VSAGLT01 v1/v2/v3 或实验 VSLRBQ01 |
| 上游提交 | 完成剩余验收后再获得提交授权；功能 PR 不带实验原始归档 |

这些是当前候选的工程设计，不是新增的官方验收指标。不加入按数据量自动切换后端：由调用方显式决定何时承担建图成本。

## 源码依据与复用范围

| 源码 | 依据 |
| --- | --- |
| include/vsag/lite/index.h、src/lite/index.cpp | Index 所有权、tl::expected、构建成功才替换后端；未开启 RaBitQ 返回 UNSUPPORTED_INDEX_OPERATION |
| src/quantization/rabitq_quantization/rabitq_quantizer.cpp | 官方 FastEncodeRaBitQ 坐标调整、中心化 split IP 和距离公式 |
| src/simd/kernels/rabitq_pack.h、rabitq_compute.h | 官方分平面打包与独立 ISA 过滤内核；不引入 Full allocator/datacell 依赖 |
| src/lite/rabitq_codec.h | 模型、正逆变换、预备编码、连续编码容器、调用方所有的解码缓冲 |
| src/lite/rabitq_filter_ip*.cpp | Generic 回退；完整 CPU 特性检查与逐文件 ISA 编译 |
| src/lite/rabitq_graph_state.h | 图查询、过滤与事务式 CRUD |
| src/lite/rabitq_backend.cpp、rabitq_snapshot.h | API 异常转换、实际格式及严格恢复 |
| src/lite/rabitq_backend_test.cpp、lite/example/rabitq_example.cpp | 生命周期、故障、损坏快照回归及公开使用示例 |

复用的是官方简单算法和内核，不声称完整复用了 Full 的16簇融合模型、图实现或存储 ABI。量化距离和重建向量都不是精确原始向量。

## 构建、模型及内存

当前安全限制：1 <= N <= 1000000、0 < D <= 2^20、2 <= degree <= 64、ef >= degree，同时检查容器容量及有限算术。Add 不能超过候选的一百万条限制。安全上限不代表已验证的实际规模能力。

现有构建按行读取源索引训练质心和翻转模型并编码，再调用 FP32 图构建取得初始拓扑，最后生成 RaBitQ 状态并成功发布。训练保留原始行顺序，分别执行有限值检查和质心累加；至多使用单行解码 scratch，不复制整个 N×D 矩阵。后续 Add/Update 使用冻结模型和量化邻居发现。初始构建保留原始源向量和临时浮点邻接表，仅用于构建的图按行读取源向量，不再拥有第二份 FP32 矩阵；峰值仍需独立测量；后续数据分布漂移仍需质量验收。

训练行指针在读取下一行 scratch 前用完。拓扑构建复用现有 FP32 图算法，同步只读源向量；成对距离使用两个独立行缓冲。借用图和行指针不逃出工厂函数，仅返回自有邻接表并转换成拓扑，在可变 RaBitQ 状态构造前释放临时邻接表。原始源索引保留至成功发布，中间分配失败时仍保持完整。

每条编码平面占 8*ceil(D/8) 字节，六个 float 元数据占24字节；模型占4D字节质心及4*ceil(D/8)字节翻转信息。运行时还包含外部 ID、哈希槽位表、邻接表容量及查询/日志缓冲。8bit 不能直接推导整个进程 RSS；构建峰值和长期 CRUD 内存必须分开测。

重建使用调用方缓冲，产生近似原空间向量。Save 必须直接保存精确模型与编码，不能解码再编码。seed 可复现性限于记录的实现/工具链；跨平台 Load 依靠已保存的翻转和质心，不承诺标准库随机分布完全相同。

## 查询路径

1. 检查 FP32 输入的维度和有限值，按固定模型变换、归一化。
2. 用3bit估计遍历，保留均匀入口和隐式槽位环；visited 防重复。
3. 无过滤时对保留候选用完整3+5bit重排；有过滤时为访问到且允许的外部 ID 计算完整估计，被拒 ID 仍可用于路由。
4. 按估计距离、外部 ID 排序返回。启发式 lower bound 不构成普适召回保证。

SearchWithOptions 的零预算沿用默认，预算受活跃数量和所需结果数约束；不改变建图、CRUD 和持久化默认配置。k=0 或删空后的索引返回空结果，过滤可能使结果少于k。

每查询变换归一化为 O(D)，每候选过滤/补充计算也与D相关，visited空间与N相关。图查询每次缓存 query_sum，完整3+5bit评分复用粗排过滤内积。每个四记录邻接批次评分前，参考原生 HGraph RaBitQ，使用只读缓存提示预取过滤码缓存行和元数据。不改变评分、遍历顺序、visited、过滤或持久化，也不分配共享查询缓冲。收益依赖维度、缓存及硬件，不承诺统一延迟改善。提高ef会增加工作量。

## CRUD、失败语义和限制

| 操作 | 当前实现 | 限制 |
| --- | --- | --- |
| Add | 验证、预备编码、预留容量、记录修改行、发布；异常回滚 | 扩容、邻居发现、日志仍有成本 |
| Update | 验证存在的ID、预备一次编码、比较平面和全部元数据，相同则跳过，否则记录编码/行后重连 | 编码相同不等于原输入完全相同；真实大幅更新可能影响模型和图质量 |
| Remove | 物理末尾搬槽；修复不对称入边；记录编码/ID/行并保留移除的map节点供回滚 | 默认不建反向边索引，可能 O(total_edges) 扫描，不能说 O(degree) |
| 内部反向边实验 | 单独可选路径 | 事务仍可能使用完整clone，不属于这次公开默认交付 |

Add/Update/Search 返回 tl::expected。分配/容量错误映射 NO_ENOUGH_MEMORY，普通输入/ID错误 INVALID_ARGUMENT，受保护的其他操作异常 INTERNAL_ERROR；损坏格式 INVALID_BINARY，写流沿用 READ_ERROR。Remove 的 bool 无法区分缺失ID与事务失败，false时原状态保留；必须说明限制，不偷偷改签名。

Build失败保留原后端，事务失败保留逻辑内容、拓扑和模型。Save失败可能留下部分写入流；原子文件替换需调用方临时文件写完后替换。没有新增并发和文件原子保证；已有分配故障测试不代表覆盖所有外部平台分配器。

## 候选快照的实际布局

除8字节magic外整数为little-endian u64；float是little-endian IEEE float32位模式，ID存int64原位模式。

| 顺序 | 内容 |
| --- | --- |
| 1 | VSAGLQ01、version=1、D、N、centroid_count=D、flip_count=4*ceil(D/8) |
| 2 | D个质心float、flip_count个字节 |
| 3 | 每条六float：norm/code_norm/error/filter_norm/filter_error/lower_bound_error；随后3*ceil(D/8)过滤字节和5*ceil(D/8)补充字节 |
| 4 | max_degree、ef_search、ID count=N、N个外部ID |
| 5 | offset_count=N+1、neighbor_count=E、N+1个offset及E个邻居槽位 |

总大小：96 + 4D + 4*ceil(D/8) + N*(40 + 8*ceil(D/8)) + 8E 字节，不包括运行时哈希/容量和文件系统开销。文件按记录交错写入，内存则为独立连续过滤/补充数组。

v1隐式固定算法常量，并没有独立保存seed/error rate/bit字段；旧提案说法已废止。Load用精确模型恢复，不重训。未来改变固定编解码/变换语义必须新增可识别版本及兼容测试，不能重新解释v1。不会仅为统一magic而迁移到VSAGLT01 v4。

加载在分配编码前检查剩余可寻址流长度，验证维度/数量/模型布局、元数据有限性和范围、ID唯一、offset、度数、邻居范围、自环/重复、截断和尾部字节。恢复的是编码和拓扑，不是原向量。浮点格式保持不变；关闭后端和错误magic的分类按Index::Load实际逻辑处理。

## 已有证据与未完成验收

以下数字引用已提交实验，并非本次重新跑实验。

| 记录（lite/benchmark/results下） | 已有结果 | 不能证明 |
| --- | --- | --- |
| integrated-load-final-20261009，10k | 三分布fresh-process loaded RSS较FP32低约41–66% | 冷IO、构建峰值、长期真实更新、普遍延迟优势 |
| integrated-100k-pilot-20261009 | 固定degree16/ef128 RaBitQ召回：SIFT .946、GIST .748、Cohere .889；loaded RSS更小 | 默认预算下质量达标 |
| integrated-100k-budget-grid-20261009 | 已观察查询选择：SIFT ef512 .975；GIST ef2048 .924；Cohere ef2048 .967 | 盲验收、精确等召回对照、重复稳定耗时、最优 |
| CRUD journal回归 | 既有公开生命周期、roundtrip和有限分配故障回滚通过 | 验收配置下长期真实整向量变化的性能质量 |

SIFT/Cohere .95、GIST .90是实验预声明floor，不是社区统一最终要求。增大ef能达到这些已观察floor，但查询比浮点更慢。RAM暖缓存加载不是冷启动磁盘实验；100k预算网格仅聚合质量，最终需要保存逐查询返回邻居，不能拿旧ef128原始结果替代高ef证据。

## 接下来按顺序完成

1. 完成可审计验收runner：复用缓存SIFT128/GIST960/Cohere768输入，10k与100k固定单核，冻结源码/配置；保存逐查询ID/距离/hits和CPU/wall，按真实变更的活跃向量集合独立重算GT。
2. 长混合Add/真实Update/Remove，覆盖整向量变化、固定模型漂移、反复ID churn、过滤及变更后持久化；记录吞吐/P50/P99、阶段召回、事务错误及fallback成本，不在运行中增预算；并发不属于本期保证。
3. 同单核、声明质量目标下比较Lite FP32/FP16/RABITQ8与Full；分别看初建和单条增删改、构建/查询CPU、包体/快照、load-only RSS及峰值，耗时用重复fresh-process。1M作为后续容量刻画可选，不替代小规模10k/100k必需验证。
4. 只优化明确成本：先缓存查询query_sum和重排所需filter值，再做标量/SIMD差分及三分布对照；若构建峰值突出，再验证不保留重复图的编码/拓扑转移，同时保留失败后发布语义。反向边另评估内存和Remove收益。这里是计划，没有冒称已实现。
5. 固定文档/安装示例/格式兼容/default-OFF；重跑Release、ASan/UBSan、format/tidy15、候选库覆盖率>=90%、损坏/故障及依赖检查；明确授权后才提取功能到PR。

## 与导师确认的边界

- 最低Recall@10、允许P99退化及内存降幅是多少？以质量对齐比较，不能只看RSS。
- 第一版本是否按单线程、固定模型和bool Remove限制交付？
- 独立候选格式及default-OFF是否适合上游，还是需要正式维护格式决策后再提交？

已有CRUD正确性、单核证据和query context优化可继续执行，不必为等待指标新增无关功能。暂不加入IP/cosine、PCA/MRQ、磁盘补充、mmap/零拷贝、在线重训、原向量精确重排、融合多簇和ARM SIMD。不在验收完成前宣称完成日期或全局最优。

### 2026-10-10 CRUD 独占阶段诊断

基于bc3e9bd在单线程RAM隔离副本插桩，生产不变。固定10k/600历史查询、degree16/维护128/查询512、三遍全ID真实UpdateRemoveAdd，GIST/Cohere CPU独占占比：nearest（含路由/评分）29.20/30.91%，入边扫描19.08/22.21%，邻居评分排序20.15/17.90%，变换后码重建13.77/11.93%，编码6.28/5.97%。时钟有开销，仅诊断，非生产收益或Full对照。有序结果/快照SHA与历史NONE control一致，Recall仍.811167/.908167。证据`lite/benchmark/results/rabitq-mutation-profile-20261010`含源码、绑定、校准/作用域夹具、180000操作/2400真值独立审计。生产测试覆盖率继承，非新跑。下一固定质量预算优先路由/扫描；100k/交错CRUD/freshFull对齐/coldIO未验收。

### 2026-10-10 拒绝批量变换码解码候选

真实生产候选复用原生RecoverOrderSQ移位掩码恢复思路，每字节批量重建8维；原浮点除法、图政策、预算、API/model/snapshot不变。256编码/尾维/未对齐/四norm逐位回归和candidate Release6/SAN5通过。固定10k GIST/Cohere600查询、NONE/NONE、三交替pair、三遍全ID真实UpdateRemoveAdd，CRUD中位+0.18484%/+1.57367%，样本内全部pair变慢，无收益，不推断普遍回退或具体CPU原因。header/test撤回为675aed7逐字节一致，restoredRelease6/SAN5、最终format/tidy15通过，默认库SHA1a18379a不变。无fresh coverage/OFF/Full全套/Node成绩。证据`lite/benchmark/results/rabitq-block-decode-20261010`独立审计1080000操作/14400真值、paired有序结果/快照SHA、183raw成员30852726B及10验证退出码。默认Recall.811167/.908167未修复。下一检索已有原生Batch4内积评分在图维护中的复用，尚未实现/测量。终验未完成，PR2904/2926未改。
