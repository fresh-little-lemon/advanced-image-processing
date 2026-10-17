# 面向曝光差异与噪声的可靠多焦点图像融合

传统多焦点图像融合的 C++ / Python 实验工程，研究曝光差异、噪声和清晰度判定之间的关系。当前版本完成可复现基线、噪声校正原型、数据清单、自动测试和第一轮验证。

## 已实现

- Python 包与命令行：均值、Laplacian 硬选择、SML 硬选择、引导滤波权重融合
- 两类实验方法：绝对响应噪声底扣除、平方响应噪声方差校正；配套逐项消融
- C++17 / OpenCV CPU 基线，与 Python 的 60 组浮点结果对照通过
- 11 项 Python 单元和命令行集成测试通过
- Lytro 20 对、EDMF 20 对探索实验；MFI-WHU 26 组验证实验；完整逐图 CSV 与配置
- x86-64 / ARM64 构建工作流；ARM64 实机结果待补充

## 安装与接口

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
python -m unittest discover -s tests -v
reliable-focus image_A.png image_B.png fused.png --method guided
```

也可直接运行已验证的源码入口：

```bash
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 python -m reliable_focus.cli \
  image_A.png image_B.png fused.png --method guided
```

```python
from reliable_focus import Config, fuse
result = fuse(image_a, image_b, Config(method="guided"))
```

实测环境为 Python 3.12.14、NumPy 2.3.5、SciPy 1.17.0、Pillow 12.3.0。C++ 直接编译使用 g++ 14.2.0 和 OpenCV 4.10；CMake 构建入口与说明见 [cpp/README.md](cpp/README.md)。

## 适用输入与数值约定

输入为已配准、同尺寸、静态场景的两幅图像。文件入口接受 8 位 RGB；数值接口接受 `[0,1]` 浮点 RGB，内部统一使用 float64。边界采用反射扩展。灰度权重为 0.299、0.587、0.114。

默认在存储的 RGB 码值上处理，与既有探索实验及 C++ 基线保持一致。`--linear-light` 显式使用 sRGB 解码、融合、编码流程。文件入口对灰度、透明通道、16 位和嵌入 ICC 的图像要求先显式转换；数据集实验采用记录在元数据中的 `encoded_ignore` 策略，评估原始码值。两种色彩处理约定应分别比较。

当前融合从原输入重建颜色；曝光归一化只影响焦点判定。曝光恢复、配准、饱和区域重建是后续独立模块。

## 方法

| 名称 | 实现 |
|---|---|
| average | 等权平均 |
| laplacian | 四邻域 Laplacian 绝对值，7×7 均值，硬选择；相同响应选 A |
| sml | 水平和垂直二阶差分绝对值之和，7×7 均值，硬选择 |
| guided | Laplacian 掩膜、7×7 中值、半径 5 / ε=0.001 的引导滤波 |
| experimental | 绝对响应噪声底扣除、局部亮度归一化、软权重与引导平滑 |
| noise_energy | 有符号 `mean(Laplacian²−20σ²)` 差、方差近似、sigmoid 权重与引导平滑 |

`guided` 是使用引导滤波原语的单尺度工程基线。完整 GFF 的多尺度分解是独立的后续复现项。`noise_energy` 的相关系数固定为 κ=4，可靠性校准尚待实验；绝对响应噪声底近似在纯噪声区域具有明确期望解释，在纹理区域会产生偏差。

## 实测结果

MFI-WHU 验证集含 26 组人工散焦图像及提供的清晰参考。平均 PSNR：

| 方法 | PSNR / dB |
|---|---:|
| average | 29.495 |
| laplacian | 36.799 |
| sml | 36.879 |
| guided | 37.792 |
| experimental | 35.689 |
| noise_energy | 36.795 |
| noise_energy 去掉噪声扣除 | 37.787 |

第一轮结果显示：当前噪声估计和扣除在此验证集上降低了质量，去掉扣除后恢复至引导基线附近。下一步用已知注入噪声的受控实验检验纹理污染噪声估计的机制。94 组 WHU 留出测试集保持封存。

Lytro / EDMF 的逐图数据与本地边缘保持指标见 [探索结果](results/exploration_v1/summary.json)。Q_local 的角度、边界和常量图像约定见实现；含噪输入时需与参考误差、边界误差和视觉检查共同解释。参考 PSNR 仅用于有清晰参考的 WHU 和程序生成实验。

单次探索计时排除解码与指标计算；稳定运行计时单独记录预热和重复次数。进程峰值 RSS 包含解释器与评估开销。PC 与 ARM64 状态分别记录，避免混用设备数据。

## 复现实验

```bash
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 python scripts/run_experiments.py \
  --pilot-root /path/to/existing/focus/pilot \
  --output results/exploration_v1 --visuals private_results/exploration_v1

PYTHONPATH=src OPENBLAS_NUM_THREADS=1 python scripts/evaluate_manifest.py \
  --manifest data/manifests/validation_v1.json --data-root /path/to/data \
  --output results/validation_v1 --visuals private_results/validation_v1
```

运行器先验证 SHA-256，再处理完整指定清单。配置、种子、每图结果、来源和设备元数据保存在结果目录。原始数据与派生图像保留在本地；仓库提供代码、清单和数值结果。数据使用遵循原始来源条款。此前使用过的 Lytro / EDMF 归为探索数据。更多数据划分和评价约定见 [数据协议](docs/data_protocol.md)、[评价协议](docs/evaluation_protocol.md)。

## 方法来源与下一步

- Nayar & Nakagawa，Shape from Focus，1994：[SML 来源](https://doi.org/10.1109/34.308479)
- He、Sun、Tang，Guided Image Filtering，2010：[引导滤波](https://doi.org/10.1007/978-3-642-15549-9_1)
- Li、Kang、Hu，Image Fusion With Guided Filtering，2013：[完整 GFF](https://doi.org/10.1109/TIP.2013.2244222)
- Xydeas & Petrovic，2000：[边缘保持评价](https://doi.org/10.1049/el:20000267)
- [Lytro](https://github.com/mnnejati/LytroDataset)、[EDMF](https://github.com/stywmy/EDMF)：探索数据来源

下一阶段优先验证噪声估计偏差、补充受控退化与可靠性校准，再固定方法并启用留出测试。完整文献比较与研究设计见 [研究方案](docs/research_plan.md)。

第一轮实验的完整范围、负结果与噪声机制诊断见 [实验记录](docs/first_experiments.md)。固定依赖版本见 `requirements-repro.txt`。当前环境还验证了复用已安装科学计算依赖的安装路径：`python -m venv --system-site-packages .venv`，随后 `.venv/bin/python -m pip install --no-deps --no-build-isolation -e .`；生成的 `reliable-focus --help` 入口正常。
