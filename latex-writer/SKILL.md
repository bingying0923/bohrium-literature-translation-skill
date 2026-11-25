---
name: latex-writer-compiler
description: 生成并校验可编译的 LaTeX 源文件：结构化组装（导言区、章节、公式、三线表、\label/\ref/\cite）、特殊字符转义、静态检查（括号/环境/引用/标签/表格列数/非 ASCII/宏包重复），并在有 TeX 发行版时实际编译、无则诚实标注"仅静态检查"。当用户要求写 LaTeX、修编译错误、检查引用标签、把内容迁进模板或需要可复现构建时使用。
version: 1.0.0
---

# LaTeX 写作与编译：编得通 + 改得对 + 复现得了

交付**能编译、能继续编辑**的 `.tex` 源码，并把每个报错定位到行号与根因。

**不做什么**：不把 PDF/截图当交付；不隐瞒"本机没编译过"；不靠缩放掩盖表格溢出。

## 1. 适用条件

- 输入：结构化内容（doc.json）或已有 `.tex` + `.bib`
- 需要：可编译源码、静态检查报告、编译记录
- 不适用：需要专有模板宏包（如期刊 .cls）而环境中没有时，只能生成源码并标注"未在目标模板下验证"

## 2. 输入

| 来源 | 说明 |
|---|---|
| `/input/case.json` | `case_id`、目标模板/期刊、TeX 引擎（pdflatex/xelatex） |
| `doc.json` | 标题、作者、摘要、章节（正文/公式/表格）、label |
| `refs.bib` | 参考文献 |

## 3. 输出（必须）

`/app/output/result.json` + `/app/output/main.tex` + `/app/output/build_report.md`

## 4. 执行流程

### Step 1 组装源码

```bash
python3 scripts/build_tex.py --doc work/doc.json --out main.tex [--template templates/article.tex]
```

- 转义：`& % $ # _ { } ~ ^ \` 全部转义，正文不裸写
- 结构：`\documentclass` → 宏包 → `\title/\author` → `\begin{document}` → 章节 → 表格 → `\end{document}`
- 每个 `\section` 可带 `\label{sec:...}`；公式用 `equation`；表格用 `booktabs` 三线表
- 中文/非 ASCII：优先 `xelatex + ctex`；用 pdflatex 时必须先转义或改引擎

### Step 2 静态检查

```bash
python3 scripts/lint_tex.py --tex main.tex --bib refs.bib --out work/lint.json
```

| 检查 | 级别 | 说明 |
|---|---|---|
| 花括号平衡 | error | 缺/多 `}` |
| 环境配对 | error | `\begin{x}` 与 `\end{y}` 不匹配、未闭合 |
| 文档结构 | error | 缺 `\documentclass` / `\begin{document}` / `\end{document}` |
| `\ref` 目标 | error | 无对应 `\label` |
| `\cite` 目标 | error | `.bib` 中不存在 |
| 表格列数 | warning | `&` 数与列声明不符 |
| 非 ASCII | warning | 需 xelatex/ctex |
| 宏包重复 | warning | 重复加载 |

### Step 3 编译（有环境时）

```bash
python3 scripts/make_result.py --tex main.tex --lint work/lint.json --compile --out /app/output/result.json
```

- 自动探测 `latexmk` / `pdflatex` / `xelatex`
- 需要多遍时用 `latexmk`（自动处理 `.aux/.bib` 轮次）；手动引擎至少 2 遍
- **本机无 TeX 时**：`build.available=false`，`note` 写明"仅静态检查，交付前需在目标环境实测"，不得声称编译通过

### Step 4 自检

1. `lint.issues` 中 error 为 0
2. 所有 `\ref`/`\cite` 都有目标
3. 交付的是 `.tex` 源码 + `.bib`，不是 PDF
4. 报告中写清引擎、宏包版本、编译命令与轮次
5. 编译警告（overfull hbox 等）记录但不掩盖

## 5. 状态与诚实性

- `status`：`success`（静态检查通过且已编译成功）/ `partial`（有 error 或未编译成功）/ `failed` / `stuck`
- `unresolved` 每条写：行号、问题、修复建议
- 禁止：声称"编译通过"而实际未跑；把错误日志截断到看不见根因

## 6. result.json 契约

```json
{
  "case_id": "",
  "status": "success|partial|failed|stuck",
  "deliverable": {"path": "main.tex", "kind": "latex"},
  "lint": {"ok": true, "errors": 0, "warnings": 0,
           "issues": [{"line": 12, "level": "error|warning", "issue": ""}]},
  "build": {"available": true, "engine": "latexmk", "returncode": 0,
            "note": "", "log_tail": ""},
  "unresolved": [{"where": "line 12", "issue": "", "suggested_action": ""}],
  "artifacts": [{"path": "main.tex", "kind": "latex"},
                {"path": "build_report.md", "kind": "markdown"}]
}
```

## 7. 异常处理

| 情况 | 处置 |
|---|---|
| 缺 TeX 发行版 | 静态检查 + 明确标注未编译 |
| 目标模板缺 .cls | 生成源码 + `unresolved` 说明"需模板文件" |
| `.bib` 缺条目 | `\cite` 报 error，补条目或删引用 |
| 非 ASCII 报错 | 改 `xelatex` + `ctex`，或转义 |
| 表格溢出 | 改 `tabularx`/`p{}` 列宽或拆表，不缩放 |
| 多遍才收敛 | 用 `latexmk` 或注明需 2-3 遍 |

## 8. 目录

```
SKILL.md                      本文件
environment/resources.yaml    资源清单
rules/latex_rules.md          转义、结构、表格、引用、编译规则
scripts/build_tex.py          结构化组装 + 转义 + 表格/公式/标签
scripts/lint_tex.py           八项静态检查（带行号）
scripts/make_result.py        编译（可选）+ 合成 result.json + build_report.md
templates/result.schema.json  输出结构
templates/article.tex         最小可用导言区模板
examples/                     最小示例（示意输出）
```
