---
name: pdf-layout-parser
description: 把论文 PDF 的版面文本解析成结构化结果：修正双栏阅读顺序、去页眉页脚、识别章节层级、抽取表格转 Markdown、保留公式与图表题注位置，并输出带页/块锚点的 document.md 与 result.json。当任务要求解析 PDF、还原多栏阅读顺序、抽取表格、识别章节结构或核对"有没有漏行错栏"时使用。
version: 1.0.0
---

# 文献文档解析：阅读顺序 + 结构 + 表格保真

把 PDF 版面文本变成**顺序正确、锚点可查**的结构化文档，而不是一段"看起来像全文"的文本。

**不做什么**：不解释科学结论、不补全缺失文字、不把图片里的公式猜出来。

## 1. 适用条件

- 输入是论文 PDF（经 `pdftotext -layout` 或平台 pdf-text-tool 得到的**保留列间距**的版面文本）
- 需要：阅读顺序正确、章节层级清楚、表格可读、公式/图表位置可查
- 不适用：纯扫描件（先走 OCR 再喂进来）、加密 PDF

## 2. 输入

| 来源 | 说明 |
|---|---|
| `/input/case.json` | `case_id`、PDF 路径、是否要表格/公式 |
| `/input/*.pdf` | 原文件；先用 `pdftotext -layout` 抽版面文本；无文字层则 OCR |
| `/input/*.txt` | 已抽好的版面文本（页边界 `[page N]` 或换页符） |

## 3. 输出（必须）

`/app/output/result.json`（契约见 §6）+ `/app/output/document.md`。

## 4. 执行流程

### Step 0 取版面文本

```bash
pdftotext -layout input.pdf work/layout.txt      # 有文字层
# 无文字层：平台 ocr-tool，OCR 后按页拼接，页边界写 [page N]
```

抽完先自检：页数是否与 PDF 一致、是否有方块乱码、每页字符数是否异常（<50 视为空页）。

### Step 1 版面修复（决定"排得对"）

```bash
python3 scripts/fix_layout.py --input work/layout.txt --out work/blocks.json [--columns auto|1|2]
```

- **页眉页脚**：在多页重复出现且长度 <90 的行，只在页首/页尾 2 行内剔除（避免误删正文重复句）
- **双栏判定**：统计"行内存在 ≥3 空格间隙且左右段都 >8 字符"的行占比，≥50% 判双栏
- **重排**：双栏页先输出左栏全部块、再输出右栏，块锚点 `bNNNN` 按输出顺序连续编号
- 单栏页不做切分，避免把表格行误拆成两栏

### Step 2 表格抽取（决定"拆得清"）

```bash
python3 scripts/extract_tables.py --input work/layout.txt --out work/tables.json
```

- 判定：连续 ≥3 行、每行 ≥2 列、各列起始位置对齐（容差 3 字符）
- 输出 Markdown 表；列数不一致 → 标"可能含合并单元格"告警
- 相邻页各有一张表 → 标"可能为续表"，需人工确认是否合并

### Step 3 结构与产物

```bash
python3 scripts/make_result.py --case-json /input/case.json \
    --blocks work/blocks.json --tables work/tables.json --out /app/output/result.json
```

- 章节识别：Abstract / Introduction / Methods / Results / Discussion / Conclusion / References 等
- 图表题注：`Figure N`、`Table N` 行单独归类，保留锚点
- 公式：`$...$`、`Eq. (N)`、`\begin{equation}` 记为公式块
- 质量报告：页数、栏数、块数、章节数、表数、图题数、公式数、告警

### Step 4 自检清单

1. 页数与 PDF 一致；每页块数不为 0（空页要说明）
2. 双栏页的左右栏内容不交叉（抽 2~3 段人工核读）
3. 表格列数、表头与原文一致；合并单元格已标记
4. 章节顺序单调递增（Abstract → … → References）
5. 图表题注没有被并进正文段落

## 5. 状态与诚实性

- `status`：`success`（结构完整、无阻断问题）/ `partial`（有告警或部分页失败）/ `failed` / `stuck`
- `issues` 必须写清：哪一页、哪一类问题、能否人工补齐
- 禁止：把 OCR 猜测的文字当原文、把合并单元格拍平成错误数据、漏页不报

## 6. result.json 契约

```json
{
  "case_id": "",
  "status": "success|partial|failed|stuck",
  "document": {"title": "", "pages": 0, "columns": 1, "source_file": ""},
  "structure": [{"name": "Methods", "page": 2, "anchor": "b0007", "blocks": 3}],
  "sections": [{"name": "Methods", "page": 2, "anchor": "b0007",
                "blocks": [{"anchor": "b0008", "type": "text|caption", "text": ""}]}],
  "tables": [{"id": "t001", "page": 3, "rows": 4, "cols": 3, "markdown": ""}],
  "figures": [{"anchor": "b0012", "page": 3, "caption": "Figure 1. ..."}],
  "formulas": [{"anchor": "b0015", "page": 4, "raw": "$E = mc^2$"}],
  "quality": {"pages": 0, "columns_detected": 1, "blocks": 0, "sections": 0,
              "tables": 0, "figures": 0, "formulas": 0, "warnings": []},
  "issues": [],
  "artifacts": [{"path": "document.md", "kind": "markdown"}]
}
```

## 7. 异常处理

| 情况 | 处置 |
|---|---|
| 无文字层 | OCR；仍失败则 `partial`，列出无法解析页 |
| 三栏/横排混排 | `--columns 1` 保序输出，标注"未自动重排" |
| 表格跨页 | 两表都保留，标"可能续表"，不擅自合并 |
| 公式为图片 | 只记位置与题注，`issues` 说明"公式为图片，未解析" |
| 页眉页脚与正文同文 | 只剔除页首/页尾 2 行内的重复行，其余保留 |
| 加密/损坏 PDF | `failed`，说明哪一步失败 |

## 8. 目录

```
SKILL.md                      本文件
environment/resources.yaml    资源清单
rules/layout_rules.md         版面判定口径（栏、页眉、表格、合并单元格）
scripts/fix_layout.py         页眉页脚剔除 + 双栏重排 + 块锚点
scripts/extract_tables.py     表格识别与 Markdown 转换
scripts/make_result.py        结构树 + result.json + document.md
templates/result.schema.json  输出结构
examples/                     最小示例（示意输出）
```
