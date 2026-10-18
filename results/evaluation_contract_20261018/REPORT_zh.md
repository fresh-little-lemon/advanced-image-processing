# 评价协议合同测试验收，2026-10-18

- 基准提交：a9a8aec964999cfc2475be786561efa4635a238c；本包为其上的独立本地补丁，不含作者算法修改
- 原有测试59/59通过；新增22项测试后共81/81通过，含19种结果记录破坏场景的拒绝测试
- 26开发/94保留测试/13外部场景，共133组，主清单与分清单一致；仅核验元数据与文件清单校验值，未读取保留集图像、未执行融合
- PSNR已修复整数溢出、尺寸广播、NaN/Inf、范围越界的静默接受；有效float64的30组随机回归与旧公式完全相等。float32将采用float64算术，可能有舍入差异；旧结果文件未改，不代表所有旧调用已被追溯审计
- SSIM仅新增本地公式测试及明确颜色域/crop/valid窗口约定，未完成官方库或MATLAB数值对照，不列论文新成绩
- 配对输入固定PCG64和A后B抽样次序；重复调用像素一致，原输入不变。八格消融共同参数一致，两校正均关时换估计器输出完全相同
- 新结果schema覆盖code/model/runtime哈希、A/B输入哈希和顺序、失败分母、显式无穷PSNR；人为改动一个方法种子，CLI正确失败并返回exit 1
- CLI元数据审计及自生成纯数学schema样例回读通过。synthetic_contract_bundle.json只有自检用途，不是新算法质量成绩
- 6个作者源文件逐一SHA-256仍与原记录一致；未调用MATLAB/Octave，78例Octave试跑仍只属兼容运行

## 边界与待办

旧10月17日协议与10月18日正式草案在主指标、亮度权重和计时设置不同，保留版本区分；没有擅自替换已冻结定义。当前已恢复的4份旧run.json均缺少新schema及三类汇总哈希，按legacy exploratory保留，不能追认正式验收。

仍待：学校登录后的MATLAB原生作者基线、独立参考指标核验、场景语义去重、最终冻结与真正未见保留集执行。报告不能声称质量提升、性能提升或正式优胜。按最新优先级，本轮只收尾工程验收，不再启动实验。

## 变更文件

修改 src/reliable_focus/metrics.py；新增 metric_contract.py、evaluation_contract.py、tests/test_evaluation_contract.py、scripts/check_evaluation_contract.py、docs/evaluation_contract.md。其余本目录文件为验收证据。复现实验命令见 docs/evaluation_contract.md。
