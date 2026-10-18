# GFF作者实现核查与消融计划

## 作者来源

论文：Shutao Li, Xudong Kang, Jianwen Hu. Image Fusion With Guided Filtering. IEEE Transactions on Image Processing, 22(7):2864–2875, 2013. DOI:10.1109/TIP.2013.2244222。

- 作者发布页：https://www.mathworks.com/matlabcentral/fileexchange/68962-a-demo-for-image-fusion
- 作者身份页：https://www.mathworks.com/matlabcentral/profile/authors/2308719
- 公开代码预览：https://viewer.mathworks.com/addons/68962/latest/files/GFF_1.0/GFF.m
- 论文记录：https://pubmed.ncbi.nlm.nih.gov/23372084/
- PDF镜像：https://github.com/RCharradi/Image-fusion-with-guided-filtering/blob/master/Image%20fusion%20with%20guided%20filtering.pdf

本目录的MATLAB文件从MathWorks公开代码预览逐行导出，保留算法及参数；换行来自网页文本导出，不声称与作者ZIP逐字节一致。默认参数r1=45、eps1=0.3、r2=7、eps2=1e-6。许可证来自发布页链接，保留版权和完整许可。未获取或执行MATLAB商业运行环境。

## 与此前适配版本的区别

作者load_images将图像按uint8读入，GFF内部除255；采用max的第一个并列最大标签，优化权重经过uint8(W*255)再归一化，最终输出uint8(F*255)。原实验中的gff_continuous_shared_gray使用线性RGB浮点输入、保留连续权重与输出，所有并列最大值均置1。它属于适配变体，既不是作者代码执行结果，也不是已证明逐像素等价的移植。

已有12变体表中的GFF数字只属于上述适配变体。正式作者基线需要独立运行记录，不能据旧表声称超过作者GFF。原结果保留用于可追溯性。

## 固定的对照与消融规范

1. 保留MFI-WHU 26开发场景；94个保留场景与13组MFFW2外部保留集继续封存。开发结果不等于最终测试结果。
2. 原版GFF保持算法及默认参数。运行环境单独标注：MATLAB原生或Octave兼容执行不可混称。先验证函数输入输出、量化、边界、并列标签和示例，再运行场景。
3. 所有方法获得同一A/B像素对。噪声在统一线性RGB域生成，再编码并量化为相同uint8输入；自研方法将同一像素对解码，不给某方法未量化的额外输入。输出统一转换至线性RGB评价，另保存显示用sRGB。
4. 无扰动、A侧噪声、B侧噪声及双侧噪声分组，种子11、23、47。原始图像噪声未知；新增噪声强度与裁剪比例单独记录。曝光变化独立设因子，不与其他开关同时混改。
5. 围绕同一融合流程设置单因素及二阶交互：估噪的独立选样/交叉采样；均值噪声扣除开/关；方差归一化开/关。不开均值和方差校正时估噪不应改变输出，作为实现一致性检查。
6. 可靠性门控与边界处理各自比较开/关；曝光补偿作为独立后续模块，未实现时不填实测。每次改变一个模块，组合实验显式列出变化，保持其余参数及输入完全相同。
7. 场景等权汇总PSNR、MAE、SSIM与固定边界区域指标。配对差值按场景报告置信区间，种子属于场景内部重复，不作为独立场景增加样本量。保存全部逐场景结果、失败例及中位例；不只选有利示例。
8. 估噪误差与融合质量分别评价。已知噪声和物理焦点掩膜的结论仅在受控轨道计算；自然照片参考误差标签不视为真实光学焦点标注。
9. 保存代码版本、来源哈希、依赖、参数、计时范围与原始输出。每个完成场景写检查点，阶段完成立即同步。预注册后如需改变设计，另建版本并解释，不覆盖原实验。

状态：作者代码已读取并保存，正式原版运行和新消融尚未完成。旧表不替代本轮实验。
