# LaTeX 写作与编译规则

## 转义（正文必做）

| 字符 | 写法 |
|---|---|
| `&` | `\&` |
| `%` | `\%` |
| `$` | `\$` |
| `#` | `\#` |
| `_` | `\_` |
| `{` `}` | `\{` `\}` |
| `~` | `\textasciitilde{}` |
| `^` | `\textasciicircum{}` |
| `\` | `\textbackslash{}` |
| 下划线/百分号在 URL | 用 `\url{}` 或 `\href{}` |

## 结构

- 导言区顺序：`\documentclass` → 编码/字体 → 数学 → 表格 → 图 → 超链接 → 自定义
- 一个宏只加载一次；`hyperref` 通常放最后
- 中文：`xelatex` + `ctex`（或 `\usepackage[UTF8]{ctex}`），**不要**在 pdflatex 下直接写汉字

## 引用与标签

- 每个 `\section` 配 `\label{sec:...}`；图 `fig:...`；表 `tab:...`；公式 `eq:...`
- `\ref{}` 必须在同文档有对应 `\label{}`
- `\cite{}` 的 key 必须在 `.bib` 中存在
- 多篇引用写 `\cite{a,b,c}`，不用逗号空格混排

## 表格

- 三线表：`booktabs`（`\toprule/\midrule/\bottomrule`）
- 列数声明与每行 `&` 数一致（`lcrp{}` 计数）
- 宽表用 `tabularx` + `X` 列，或 `p{0.45\textwidth}` 换行，**不要**用 `\resizebox` 压缩掩盖溢出
- 跨页长表用 `longtable`

## 公式

- 单行带号：`equation`；多行对齐：`align`；不编号：`equation*`
- 单位用 `siunitx`（`\SI{0.8}{\micro\gram\per\liter}`）或正体 `\mathrm{}`
- 变量斜体、单位正体，不要混用

## 编译

- 引擎：`latexmk -pdf` 或 `xelatex -interaction=nonstopmode`
- 需要多遍：`latexmk` 自动；手动至少 2 遍（`.aux`、`.bib`、交叉引用）
- 记录：引擎版本、宏包版本、命令、轮次
- 报错定位：先看第一个 `!` 错误的行号与上下文，再看 `l.NN` 行
