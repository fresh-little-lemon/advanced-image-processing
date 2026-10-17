# 文献、作者实现与复现状态

核验日期：2026年10月17日。下表依据论文出版页面、作者预印本及论文直接指向的代码页面整理。状态按页面核验、依赖检查、实际运行和结果复现记录。表内“未运行”表示本轮尚未执行该作者实现。项目自编基线的运行结果另以实验日志为准。

## 核心传统方法

| 工作 | 原始来源与作者代码 | 已有机制及与本研究的关系 | 当前核验状态 |
|---|---|---|---|
| Image Fusion with Guided Filtering，Li、Kang、Hu，IEEE TIP 2013 | [作者论文](https://xudongkang.weebly.com/uploads/1/6/4/6/16465750/tip1.pdf)；[作者代码主页](https://sites.google.com/view/xudongkang/paperscodes)；[作者MATLAB示例](https://www.mathworks.com/matlabcentral/fileexchange/68962-a-demo-for-image-fusion) | 双层分解和引导权重融合。引导滤波与基础／细节分离属于继承模块 | 论文、作者主页及示例页已核验；作者程序未运行。项目另有独立实现的简化引导基线 |
| Multi-focus Noisy Image Fusion using Low-Rank Representation，Li、Wu、Durrani，arXiv 2018，修订2022 | [作者预印本](https://arxiv.org/abs/1804.09325)；[作者仓库](https://github.com/hli1221/imagefusion_noisy_lrr) | 多尺度低秩表示处理含噪融合。构成含噪条件的直接传统对照 | 仓库README及main.m入口已核验；MATLAB与变换工具依赖未安装核验，未运行；商业许可未核实 |
| Guided filter-based multi-focus image fusion through focus region detection，Qiu等，2019 | [出版原文](https://doi.org/10.1016/j.image.2018.12.004) | 均值／差分焦点检测与引导优化，已有噪声鲁棒性研究 | 论文页面已核验；本轮未确认作者代码链接，未运行 |
| Multifocus Image Fusion Based on Fast Guided Filter and Focus Pixels Detection，Zhou等，IEEE Access 2019 | [作者仓库](https://github.com/lxs6/FGF_multifocus_image_fusion) | 快速引导滤波与焦点像素检测，属于速度及质量基线 | README将仓库与论文直接关联，script.m入口；仅研究使用许可；未运行 |
| Efficient Misalignment-Robust Multi-Focus Microscopical Images Fusion，Liang等，Signal Processing 2019 | [作者预印本](https://arxiv.org/abs/1812.08915)；[出版DOI](https://doi.org/10.1016/j.sigpro.2019.03.020)；[作者JointRF仓库](https://github.com/yiqingmy/JointRF) | 复用SURF检测中的Hessian信息用于配准和融合。计算复用及错位鲁棒性已有先例 | 原论文直接链接仓库；README称C++与OpenCV3.0实现，含15组显微数据；未编译运行，许可未核实 |
| New insights into multi-focus image fusion: A fusion method based on multi-dictionary linear sparse representation and region fusion model，Wang等，Information Fusion 2024 | [出版原文](https://doi.org/10.1016/j.inffus.2024.102230)；[作者MDLSR_RFM仓库](https://github.com/JWatawang/MDLSR_RFM) | 多字典线性稀疏焦点检测、边界matting和区域修正。是强传统区域基线 | 论文直接给出仓库；main.m和核心mdlsr_rfm.p可见，核心为MATLAB受保护代码，可审计范围主要为调用入口；未运行 |
| Multi-focus image fusion based on multiscale fuzzy quality assessment，Li等，Digital Signal Processing 2024 | [出版原文](https://doi.org/10.1016/j.dsp.2024.104592)；[作者MFQA仓库](https://github.com/JWLi2023/MFQA) | 多尺度模糊质量、能量加权改进拉普拉斯与一致性检查。可靠区域与失败区域再优化已有重叠 | 原文指向仓库；MFQS目录及RAR存在；依赖、许可与运行结果未核验，未运行 |
| Multi-focus image fusion using adaptive patch rendering anisotropic diffusion filter，Tatekalva等，Scientific Reports 2025 | [出版原文](https://doi.org/10.1038/s41598-025-97323-6) | 自适应图块与各向异性扩散改善边界。可用于比较局部精化的处理策略 | 原文已核验；数据声明为合理请求提供，本轮未找到作者公开代码链接；未运行 |
| Multi-Focus Image Fusion Using Soft Decision Maps and Dual Fusion Rules，Lopez-Morales等，Electronics 2026 | [出版原文](https://doi.org/10.3390/electronics15132868)；[作者Python仓库](https://github.com/BraulioLM/multifocus-soft-decision-dual-fusion) | Tenengrad局部焦点、软权重、加性／乘性融合。软决策和低成本融合已有直接近期对照 | 论文于2026-07-01发表，出版页直接链接仓库；run_lytro.py及run_mfi_whu.py可见；README限学术研究；未运行 |

## 成像、曝光与数据依据

| 工作 | 原始来源 | 对实验的影响 | 状态 |
|---|---|---|---|
| Practical Poissonian-Gaussian noise modeling and fitting for single-image raw-data，Foi等，IEEE TIP 2008 | [作者原文](https://webpages.tuni.fi/foi/papers/Foi-PoissonianGaussianClippedRaw-2007-IEEE_TIP.pdf) | 信号相关噪声与截断是已有模型。本研究以该模型开展清晰度方差传播分析 | 论文来源已核验；无作者估计器运行记录 |
| Robust Multi-Exposure Image Fusion: A Structural Patch Decomposition Approach，Ma等，2017 | [作者机构原始记录](https://research.polyu.edu.hk/en/publications/robust-multi-exposure-image-fusion-a-structural-patch-decompositi/) | 在多曝光任务中分离结构、强度和均值，为亮度与焦点证据分离提供邻近方法依据 | 机构论文摘要已核验；未运行 |
| Multi-exposure image fusion via perception enhanced structural patch decomposition，Zhang等，2023 | [出版原文](https://doi.org/10.1016/j.inffus.2023.101895)；[论文指向代码](https://github.com/Junchao2018/PESPD-MEF) | 感知增益与结构分解为曝光处理邻近工作，需区分曝光观感与焦点来源正确性 | 出版页面已核验；代码链接由原文提供，本轮未独立打开仓库，未运行 |
| EDMF: A New Benchmark for Multi-Focus Images with the Challenge of Exposure Difference，2024 | [出版原文](https://doi.org/10.3390/s24227287)；[作者全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC11598213/)；[作者数据仓库](https://github.com/stywmy/EDMF) | 1000对真实场景，曝光差异是既有任务。真实图像适合无参考质量与接缝分析 | 原文正文已通过搜索索引核验；后续直接访问遇到验证码／限流。具体已下载数据与划分由数据清单记录 |

## 机制差异与证据门槛

拟研究机制检验“噪声校正后差值→经验可靠性→单位计算收益”的联系。与LRR及Qiu方法比较，需要证明变化发生在来源误判风险而非单纯去噪。与MFQA和软决策双规则比较，需要证明方差归一化及校准优于普通软权重。与MDLSR_RFM比较，需要区分边界扩散修正和噪声引起的来源误选。与JointRF比较，需要报告配准、融合和复用开销各自的贡献。

后续文献分析将沿这些论文的全文、附录和引用链，补充选择性预测、决策风险校准、传统焦点度量统计与自适应计算研究，进一步明确完整验证链的机制差异。

## 实验纳入与实现管理

首轮可运行内部基线采用均值、局部清晰度硬选择和简化引导融合，并明确标注独立实现。较强作者基线优先纳入2026软决策双规则、MDLSR_RFM、MFQA和含噪LRR。复现记录包含MATLAB版本、工具箱、核心保护文件、运行输出和错误日志。

每个外部实现固定仓库提交、文件哈希、原始入口、参数修改、输入预处理、输出裁剪和计时边界。参考结果与重实现结果分开列出。研究用途代码与工业核心隔离；C++产品核心采用独立实现，第三方依赖逐项记录许可证。

截至本文件核验时，所有表列外部作者程序均未在本研究分支中执行。后续运行结果以对应日志更新。
