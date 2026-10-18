# 新重建验证结果（2026-10-18）

## 恢复性质

本目录根据恢复的原 Python 规范重建 C++17 估计器，未声称找回已丢失的原 C++ 文件。
历史 28 组一致性、10 组 native 校验及旧计时不作为本轮实测。本轮保存源码、测试、固定规范、测量原始样本与环境清单。

## 本轮实际执行

- Python / C++ 对照：59/59 通过；sigma 最大绝对误差 6.2450045135165055e-17，四个 fold variance 最大绝对误差 2.7755575615628914e-17
- C++ native：25/25 通过
- 畸形 CLI 输入：10/10 通过
- AddressSanitizer + UndefinedBehaviorSanitizer：25 项 native 检查通过，stderr 为空
- LeakSanitizer：首次因当前运行环境的 ptrace 不兼容而退出；成功的 ASAN/UBSAN 运行关闭了泄漏检测，未验证无内存泄漏

## 估计器 CPU 计时

每个尺寸预热 5 次、测量 30 次，单线程，含两幅输入的校验、临时分配、支持域、灰度、高通、选块和估计；不含解码、完整融合、评价或进程启动。

- 640×480：中位数 12.883195 ms
- 1280×720：中位数 36.718422 ms
- 1920×1080：中位数 79.922570 ms

测量设备：AMD EPYC 9V74 80-Core Processor / x86_64；共享云 CPU、未绑定核心。每次样本、分位数与离散程度见 results/benchmark.json。

## 范围限制

只验证 crossfit 噪声估计器，未验证 C++ 完整融合管线，未做 ARM 实机测试。
原 Python 模型在纹理、相关噪声、裁剪和弱支持条件下仍可能偏差，本次移植没有改变或解决这些统计局限。

复现：bash build_and_test.sh results_rerun
校验：sha256sum -c MANIFEST.sha256
