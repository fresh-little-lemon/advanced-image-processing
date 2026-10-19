# 高级图像处理小测讲义 LaTeX 重构

依据用户上传的《高级图像处理_小测复习讲义_黑白打印版.pdf》（原稿10页），忠实保留模块、题目、答案和数值，将公式、矩阵、表格重建为可编辑LaTeX，重新分页为13页A4。

重排PDF采用黑白样式。原文技术疑点另列于《原稿公式核对说明.md》，未擅自更改正文；这不是新编课程讲义，也不是对原文考试预测的认证。

## 编译
安装XeLaTeX/TeX Live，含fontspec、amsmath、amssymb、booktabs、array、tabularx、longtable、enumitem、graphicx、xcolor、tikz、fancyhdr、hyperref，以及Noto CJK和DejaVu Sans Mono字体。

主文件reconstruction.tex；partA.tex对应原稿1–3页，partB.tex对应4–7页，partC.tex对应8–10页。

运行 `bash build.sh`。字体路径使用Linux Noto安装目录；其他系统请调整主文件字体路径或改为系统已有字体名称。

PDF与源文件校验见SHA256SUMS.txt。附件平台可能添加来源元数据，导致附件字节哈希与本地编译稿不同。
