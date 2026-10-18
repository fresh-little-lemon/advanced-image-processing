# 2026-10-18 恢复材料与作者 GFF pilot 清单归档

## 范围与状态

本目录补充此前仅保留在工作目录中的恢复脚本、数据恢复清单和作者 GFF pilot 用例清单。此次只做路径可移植化与归档，没有重新下载或解压数据，没有重新运行任何实验，也没有生成新的质量指标。文件追加在既有 `results/recovery_20261018` 目录下，不替换现有正式结果。

作者 GFF pilot 对应原有 26 个开发场景、3 种噪声条件、固定种子 11，共 78 个用例。它是 Octave 兼容执行的输入/运行记录辅助材料，不是 MATLAB 原生等价验证、三种子正式消融或保留集最终评测。当前评价范围以 `baselines/gff_author/FORMAL_EVALUATION_PROTOCOL.md` 为准。

不包含原始数据、输入/输出图像、音频、安装环境或任何凭据。

## 文件

- `gff_pilot/cases.json`：历史用例 ID、场景、噪声条件、种子、输入 SHA-256 及路径。仅修改 a、b、gt 三个路径字段，其余值与原文件一致。
- `gff_pilot/cases.tsv`：历史 wrapper 使用的四列清单（无表头）：用例 ID、A 输入、B 输入、作者输出；只替换绝对路径前缀。
- `extract_validation.py`：恢复 26 个开发场景的 78 个文件的原脚本。保留 RAR 哈希、逐文件哈希、开发集和文件数检查；仅调整仓库根和本地数据根的定位。
- `data_restoration.json`：原恢复运行产生的清单，字节未改；记录 78 个恢复文件和 0 个提取的保留集文件。它是历史证据，不表示本次又执行了恢复。
- `provenance.json`：原文件及归档文件哈希、路径修改说明和静态校验结果。
- `SHA256SUMS`：本目录除其自身外的全部文件 SHA-256。

## 路径约定与手动使用

JSON 和 TSV 中所有路径都相对仓库根目录：pilot 输入/输出位于 `baselines/gff_author/pilot/inputs` 和 `baselines/gff_author/pilot/outputs`；GT 位于 `data/MFI-WHU/...`。这些文件在本归档中只有路径与哈希，实际图像需由使用者在有权访问的本地数据环境准备。

清单保存在归档目录，不会被现有 wrapper 自动读取。若在另一次明确启动的复现中使用，先在仓库副本准备匹配的图像，并将清单置于该副本的 `baselines/gff_author/pilot/cases.tsv`，从仓库根目录运行。此处没有修改或执行现有 `prepare_pilot.py` 和 `run_author_pilot.m`；它们原有的环境约束仍需检查。

恢复脚本从本文件所在的仓库根读取 `data/manifests/validation_v1.json`。默认从仓库根的 `MFI-WHU.rar` 读取归档，将恢复数据写入仓库根的 `data/`，并在仓库根写 `data_restoration.json`。可通过环境变量 `FUSION_REPRO_ROOT` 指定另一个本地工作目录；此时从该目录读取 `MFI-WHU.rar`，将数据和新运行清单写入该目录，仓库 manifest 的读取位置不变。若数据根不在仓库内，使用 pilot 清单前需映射相应路径。

脚本依赖 Python 和系统 libarchive；此次只进行了 AST 语法检查，没有验证当前机器上的解压依赖或重跑恢复。手动执行脚本会创建/覆盖所选工作目录中的匹配数据文件和恢复清单，宜使用单独的工作目录。本归档没有执行该操作。

## 既有材料对应关系

- 正式方案、作者源文件、运行时间和输出 inventory 已在 `baselines/gff_author/`，本目录只补充用例清单。
- 旧本地 `make_comparison.py` 的可移植版本已在 `scripts/render_recovery_comparison.py`；其差异为目录定位，不再次发布旧脚本或覆盖当前版本。
- 既有比较和汇总见 `docs/current_comparison_and_ranking.md`、`results/recovery_20261018/all12_ranking.json` 和原始逐场景 CSV；本次不以旧汇总冒充新结果。
