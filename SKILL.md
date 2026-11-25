---
name: literature-translation-bilingual
description: 把科研论文（PDF/纯文本）翻译成"术语锁定 + 段落对齐 + 可核验"的中英双语对照结果。自动完成分段编号、术语抽取与全篇锁定、逐段翻译、数字/单位/公式/引用/否定核验，并输出带原文定位的 result.json。当任务要求翻译文献、论文、摘要、图表题注，或要求术语统一、双语对照、译文可回溯原文时使用。
version: 1.0.0
---

# 文献翻译：术语锁定的双语段落对照

把一篇真实文献译成**可核验的双语对照**：每一段译文都能指回原文的页码与段号，
同一个术语在全篇（标题、摘要、正文、图注、结论）只用一个译名，数字/单位/公式/引用/否定关系逐项校验。

**不做什么**：不写摘要代替翻译，不改写原文，不补造原文未报告的数据，不把示意输出当正式答案。

## 1. 适用条件

- 输入是一篇论文/章节/摘要区间的 PDF 或文本，需要中英对照
- 读者需要"回看原文"：段落能定位、术语能追溯、译不准的地方要显式标出
- 不适用于：纯图片扫描件（需先 OCR）、多语混排无主语言的文档（先判主语言）

## 2. 输入

| 来源 | 说明 |
|---|---|
| `/input/case.json` | 案例标识 `case_id`、材料路径、任务要求；以实际文件内容为准，不要凭字段名猜内容 |
| `/input/*.pdf` 或 `task.md` 指定材料 | 论文本体；优先读文字层，无文字层再 OCR |
| 已有术语表（可选） | CSV：`term,translation,locked,note`，`locked=true` 的必须沿用 |

## 3. 输出（必须）

`/app/output/result.json`，字段契约见 §6；同时给出便于人看的两份衍生件：

- `/app/output/bilingual.md`：段落级双语对照（段号 + 原文 + 译文 + 定位）
- `/app/output/glossary.csv`：本次锁定的术语表

## 4. 执行流程

### Step 0 读题与边界（先做，不要跳）

1. 读 `task.md` 与 `case.json`，确认：翻译范围（全文/摘要/某章节区间）、目标语言、是否要术语表、证据定位粒度。
2. 确认材料真实存在并记录文件名、页数、是否可提取文字层。
3. 把"任务要求"落到 `work/plan.json`：`{scope, target_lang, need_glossary, locator_level}`。

### Step 1 取文本

```bash
# PDF 有文字层：直接抽取，保留分页
pdftotext -layout input.pdf work/source.txt        # 有 pdftotext 时
python3 scripts/segment_text.py --input work/source.txt --out work/segments.json --lang en
```

- 无文字层或抽取结果为空：走 OCR（平台提供 ocr-tool），OCR 文本按页拼接，页边界写入 `[page N]`
- 抽取后必须**自检**：字符数、是否出现乱码方块、页数是否与 PDF 一致；不合格就换方式并在 `uncertainties` 记录

### Step 2 分段与编号（决定"段落全"）

`scripts/segment_text.py` 规则：

- 以空行/换行+缩进断段；页边界（`\f` 或 `[page N]`）不断段，只记录页码
- 识别章节标题（`Abstract`、`1 Introduction`、`2.1 Method`、`References`、`Figure 1.`、`Table 2.`）
- 每段给出稳定段号 `p001…`，并记录 `page`、`section`、`char_len`
- 参考文献条目单独标 `section=References`，**不翻译**，只保留原文

产物：`work/segments.json`（段号、页码、章节、原文）。

### Step 3 术语表（决定"术语稳"）

```bash
python3 scripts/build_glossary.py --segments work/segments.json --out work/glossary.csv
```

- 自动抽取候选：大写多词短语、缩写（≥2 个大写字母）、连字符术语、希腊字母/单位、高频名词短语
- 每个候选保留首次出现位置与上下文（便于判断）
- 译名确定后写回 `translation` 列并置 `locked=true`；**先锁术语再翻译正文**，不要边译边改
- 已有术语表（`--existing`）中的 `locked=true` 条目优先级最高，冲突时保留旧译名并在 `uncertainties` 记录

### Step 4 逐段翻译（决定"关系准"）

- 按 `p001…` 顺序逐段翻，**不合并、不拆分、不跳段**；每段只输出该段译文
- 每段携带：前一段末句（上下文）、本段命中的术语及其锁定译名
- 硬性规则：
  - 术语按表译，表里没有的先补表再译（补表要记录）
  - 数字、单位、公式、图表编号、文献引用标记 `[12]`、`(Smith et al., 2020)` **原样保留**
  - 否定（not / no / none / fail to / 不 / 未 / 无）与限定（only / may / suggest / 可能 / 提示）必须译出，不得加强或弱化
  - 指代（this / these / it / the former）要还原成具体对象，不保留"这/它"
  - 译不准或原文残缺：译文中标 `【存疑：原因】`，并进 `uncertainties`，不要含糊带过

### Step 5 核验（决定"可核验"）

```bash
python3 scripts/check_translation.py \
  --segments work/segments.json --translations work/translations.json \
  --glossary work/glossary.csv --out work/checks.json
```

自动检查并给出问题清单：

| 检查项 | 判据 |
|---|---|
| 数字 | 原文数字集合 ⊆ 译文数字集合（允许千分位/全角差异） |
| 单位 | `mg/L`、`℃`、`kPa`、`%` 等符号在译文中保留 |
| 引用 | `[n]`、`(Author, Year)` 数量与位置不丢失 |
| 公式 | `$...$`、`Eq. (3)`、上下标标记保留 |
| 图表 | `Fig. 1`、`Table 2` → `图 1`、`表 2`，编号一致 |
| 否定 | 原文否定词与译文否定词同现（漏译/多加都报） |
| 术语一致率 | 每个锁定术语在命中段落中的译名一致率；不一致逐条列出 |

核验不通过的段落必须**回改**，改完重跑，直到通过或写入 `uncertainties`。

### Step 6 产出

```bash
python3 scripts/make_result.py --case-json /input/case.json \
  --segments work/segments.json --translations work/translations.json \
  --glossary work/glossary.csv --checks work/checks.json \
  --out /app/output/result.json
```

同时写 `bilingual.md` 与 `glossary.csv`（脚本已包含）。

## 5. 状态与诚实性

- `status`：`success`（范围内全部译完且核验通过）/ `partial`（有未译段落或核验未过）/ `failed` / `stuck`
- 每个未完成项都要能说出**卡在哪**：缺文字层、公式为图片、原文残缺、超出预算
- `uncertainties` 每条包含 `segment_id`、`issue`、`why`、`suggested_action`
- 禁止：把示意输出当案例结果；用摘要冒充全文翻译；编造页码或文献编号

## 6. result.json 契约

```json
{
  "case_id": "由 case.json 读取，原样回填",
  "status": "success|partial|failed|stuck",
  "language": {"source": "en", "target": "zh"},
  "document": {"title": "", "pages": 0, "source_file": "", "has_text_layer": true},
  "glossary": [{"term": "", "translation": "", "locked": true,
                "occurrences": [{"segment_id": "p003", "page": 1}],
                "note": ""}],
  "segments": [{"id": "p001", "section": "Abstract", "page": 1,
                "source": "", "translation": "",
                "terms": [""], "confidence": "high|medium|low", "note": ""}],
  "checks": {
    "numbers": {"ok": true, "issues": []},
    "units": {"ok": true, "issues": []},
    "citations": {"ok": true, "issues": []},
    "formulas": {"ok": true, "issues": []},
    "figures_tables": {"ok": true, "issues": []},
    "negation": {"ok": true, "issues": []},
    "term_consistency": {"rate": 0.0, "violations": []}
  },
  "untranslated": [{"segment_id": "p012", "reason": ""}],
  "uncertainties": [{"segment_id": "", "issue": "", "why": "", "suggested_action": ""}],
  "artifacts": [{"path": "bilingual.md", "kind": "markdown"},
                {"path": "glossary.csv", "kind": "csv"}],
  "run": {"tool_versions": {}, "notes": ""}
}
```

## 7. 异常处理

| 情况 | 处置 |
|---|---|
| PDF 无文字层 | OCR；仍失败则 `status=partial`，列出无法解析的页，保留可解析部分 |
| 公式/表格是图片 | 保留图号与题注位置，译文写 `【公式见原图 Eq.(3)】`，进 `untranslated` |
| 参考文献无法解析 | 不翻译，原文照录，`section=References` |
| 原文残缺/乱码 | 该段标 `【原文残缺】`，进 `uncertainties`，不猜补 |
| 语言混杂 | 先判主语言；非主语言段落原文保留并标注 |
| 超时/预算不足 | 先落盘已完成段落（`partial`），再补 |

## 8. 自检清单（提交前逐条过）

1. 段号连续、无缺号、无重复；段数与原文段落数一致
2. 每个锁定术语在全部命中段落译名一致（一致率 = 1.0 或已列出例外）
3. 数字/单位/引用/公式/图表编号零丢失（或已写入 issues）
4. 每段译文都有 `page` + `section`，能回查
5. `untranslated` + `uncertainties` 覆盖所有没做好的地方
6. `bilingual.md` 与 `result.json` 的段落内容一致

## 9. 目录

```
SKILL.md                     本文件
environment/resources.yaml   资源清单（入口）
scripts/segment_text.py      分段编号
scripts/build_glossary.py    术语候选抽取与术语表合并
scripts/check_translation.py 数字/单位/引用/公式/否定/术语一致性核验
scripts/make_result.py       合并输出 result.json + bilingual.md + glossary.csv
templates/result.schema.json 输出结构定义
templates/glossary_template.csv 术语表模板
examples/demo_*.md|csv|json   最小调用示例（示意输出，非正式案例结果）
```
