# 多焦点融合对比与完整排名

## 评测口径

MFI-WHU固定26个开发场景，各场景等权；原作者提供的自然照片人工散焦焦点对及全清晰参考。噪声在解码后的线性RGB中加入，标准差5/255，随机种子11，两幅图像均按原实验顺序抽样并裁剪至[0,1]。PSNR为全图线性RGB指标，越高越好。这里没有测试曝光差异，也不是94个保留场景的最终测试。

表中数值从已恢复且已发布的原始CSV重新汇总；三张示例图为本轮按同一实现、同一输入重新运行生成。

## 全部12种方法与变体

| 方法/变体 | 干净输入 PSNR | 仅B加噪 PSNR | 仅A加噪 PSNR |
|---|---:|---:|---:|
| crossfit_residual_mean | 37.807 | 34.770 | 36.265 |
| calibrated_residual_mean | 37.790 | 34.758 | 36.408 |
| crossfit_residual_full | 37.811 | 34.681 | 36.283 |
| independent_guide | 37.792 | 34.674 | 36.224 |
| shared_delta | 37.777 | 34.664 | 36.203 |
| independent_residual | 37.807 | 34.562 | 35.743 |
| shared_residual | 37.797 | 34.559 | 35.723 |
| residual_full | 37.811 | 34.407 | 35.639 |
| no_mean | 37.834 | 34.019 | 34.461 |
| residual_variance_no_mean | 37.833 | 33.779 | 34.282 |
| gff_continuous_shared_gray | 38.695 | 33.701 | 33.490 |
| guided | 37.769 | 33.244 | 33.443 |

干净输入最高为GFF连续精度复现；B加噪最高为crossfit_residual_mean；A加噪最高为calibrated_residual_mean。均值排名不代表每幅图都优于对照。

## 方法来源

- gff_continuous_shared_gray：基于Li、Kang、Hu, Image Fusion With Guided Filtering, IEEE TIP 2013，DOI 10.1109/TIP.2013.2244222 的独立Python复现；采用连续精度及共享灰度引导配置，不是作者原版MATLAB跑分。原版MATLAB数值等价尚未实测。论文：https://xudongkang.weebly.com/uploads/1/6/4/6/16465750/tip1.pdf
- guided：简化引导滤波工程基线，不是另一篇论文的完整复现。
- shared_delta及其他残差变体：本项目研究实现及消融。crossfit_residual_mean是当前交叉采样＋均值校正方法；calibrated_residual_mean使用固定选择偏差标定；full另外加入方差归一化。
- 数据：https://github.com/HaoZhang1018/MFI-WHU ，固定来源提交6071f2909f5563ccb9bcd71317f5102eefe13e6f。

## 三张示例图

每张依次为输入A、输入B、参考GT、GFF复现、当前crossfit；下排同位置放大。WHU-018与WHU-077是26组B加噪场景中相对GFF的最大PSNR提升和最大退步例；WHU-097为干净示例，其场景来自B加噪增益排序的中间位置。放大位置自动选择两种算法局部绝对误差差异最大的区域，不能代表整幅图。

WHU-018可见降噪收益；WHU-077出现更干净但保留模糊结构的失败；WHU-097干净输入上GFF更高。图像显示为sRGB，指标在线性RGB计算。没有将三张合成纹理旧图冒充本次照片数据。

## 当前工程恢复

原42文件从用户附件按字节恢复，远端42/42 Git blob SHA核对通过。后续C++根据Python规范重新实现，28文件远端核对通过。新C++59项数值对照、25项native检查及10项异常输入检查通过，ASAN/UBSAN通过，LeakSanitizer受环境限制未验证；测试计时仅估计器，不含完整融合，未测ARM。
