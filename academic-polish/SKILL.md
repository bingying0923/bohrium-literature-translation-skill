---
name: academic-polish-minimal-edit
description: 对学术稿件做"最小编辑"式润色，输出润色全文 + 逐句修改记录（原文/改文/修改类型/理由），并在改动后自动核查限定强度、数字单位、引用编号、图表指向、否定范围与术语一致性是否被改动。当用户要求润色论文、摘要、投稿信、审稿回复、基金申请书，或要求"只改语言不改意思""给出修改理由""术语统一"时使用。
version: 1.0.0
---

# 学术语言润色：最小编辑 + 可核验修改记录

把一段学术文本改成**更像同行写的、但主张强度一点没变**的版本，并且每一处改动都能说清楚：改了哪、为什么改、属于哪类修改。

**不做什么**：不整段重写、不替作者加结论、不改数据与引用、不把 "may" 改成 "demonstrates"。

## 1. 适用条件

- 输入是一段/一节学术文本（论文、摘要、引言、审稿回复、基金申请），需要语言层面的润色
- 读者需要"逐句核对"：哪句改了、改了什么类型、依据是什么
- **不适用**：内容层面的重写、补实验、补文献、翻译（翻译用另一个 skill）

## 2. 输入

| 来源 | 说明 |
|---|---|
| `/input/case.json` | `case_id`、材料路径、目标文体（期刊论文/学位论文/基金/审稿回复）、读者 |
| `/input/*.md`、`*.txt`、`*.tex` | 待润色稿件；LaTeX 片段按原样保留命令与环境 |
| 术语表（可选） | CSV：`term,preferred,locked,note`；`locked=true` 的写法必须沿用 |

## 3. 输出（必须）

`/app/output/result.json`（契约见 §6），以及两份人读产物：

- `/app/output/polished.md`：润色后的完整文本（保持原章节/段落结构）
- `/app/output/changes.csv`：逐条修改记录 `unit_id,original,revised,change_type,reason,risk`

## 4. 执行流程

### Step 0 读要求

记录：目标文体、读者、是否限定"只改语言"、有没有指定期刊风格、术语表。写进 `work/plan.json`。

### Step 1 切分到句（决定"讲得清"）

```bash
python3 scripts/segment_sentences.py --input input.md --out work/units.json
```

- 段落号 `p01…`，句子号 `p01.s01…`；段落与句子边界稳定可复现
- 保护块（不参与改写）：`$...$`、`\begin{...}...\end{...}`、`[12]`、`(Smith et al., 2020)`、URL、DOI
- 记下每句的：数字、单位、引用、图表指向、限定词、否定词

### Step 2 建立/沿用术语表（决定"术语稳"）

```bash
python3 scripts/build_terms.py --units work/units.json --out work/terms.csv [--existing old.csv]
```

- 抽候选：多词术语、缩写（首次出现要给全称）、连字符词、希腊字母/单位
- 确定 `preferred` 写法后 `locked=true`；全篇按此回扫，不一致的列进 `terms_violations`

### Step 3 分句润色（核心：最小编辑）

对每个 `unit`，按 `rules/style_guide.md` 执行，**只允许**以下几类动作：

| 类型 | 允许 | 禁止 |
|---|---|---|
| `grammar` | 主谓一致、时态、冠词、介词、单复数、悬垂修饰、标点 | 改变句子信息结构 |
| `terminology` | 按术语表统一写法、缩写首次展开 | 换成同义但不同概念的词 |
| `register` | 去口语化/宣传化、人称与语域调整 | 把"可能"改成"证明" |
| `clarity` | 长句切分、冗余名词化拆解、连接词修正 | 合并/删除信息 |
| `format` | 数字与单位空格、大小写、连字符 | 改数值本身 |

**硬约束（违反即视为改坏）**：

1. 限定强度守恒：`may / might / could / suggest / indicate / appear / tend / likely / possibly / in part` 不得删除或升级为 `demonstrate / prove / confirm / show that`
2. 数字、单位、百分比、样本量、p 值、置信区间**逐字符保持**
3. 引用编号 `[n]`、作者-年份、DOI 不改
4. 图表指向 `Fig. 3`、`Table 2`、`Eq. (5)` 不改
5. 否定范围不变：`not all`、`no significant`、`did not` 不得移位或弱化
6. 不新增原文没有的事实、比较或因果

### Step 4 自动核查（决定"没改坏"）

```bash
python3 scripts/audit_edits.py --units work/units.json --revised work/revised.json \
    --terms work/terms.csv --out work/audit.json
```

逐句比对并报告：数字/单位/引用/图表/否定/限定词/术语 是否守恒；给出 `blocking`（必须回改）与 `warning`（需人工确认）两级。

### Step 5 产出

```bash
python3 scripts/make_result.py --case-json /input/case.json --units work/units.json \
    --revised work/revised.json --terms work/terms.csv --audit work/audit.json \
    --out /app/output/result.json
```

生成 `result.json`、`polished.md`、`changes.csv`（用 difflib 逐句 diff，自动打 `change_type`）。

### Step 6 自检

1. 每个 unit 都有 original 与 revised（未改的也要在 changes 里标 `no_change`）
2. `audit.blocking` 为空，或已在 `uncertainties` 说明原因
3. 术语一致率 = 1.0，或列出例外
4. `polished.md` 与 `result.json` 的 revised 完全一致
5. 限定词统计：原文 vs 改文的数量与强度分布一致

## 5. 状态与诚实性

- `status`：`success`（范围内全部处理且核查通过）/ `partial`（有 blocking 未解或超预算）/ `failed` / `stuck`
- `uncertainties` 每条写：`unit_id`、`issue`、`why`、`suggested_action`
- 禁止：把"重写"当润色、删掉限定词、顺手改数字、编造修改理由

## 6. result.json 契约

```json
{
  "case_id": "",
  "status": "success|partial|failed|stuck",
  "genre": "journal-article|thesis|grant|response-to-reviewer",
  "summary": {"units_total": 0, "units_changed": 0, "blocking": 0, "warnings": 0,
              "term_consistency": 1.0, "hedge_preserved": true},
  "glossary": [{"term": "", "preferred": "", "locked": true, "occurrences": ["p01.s02"]}],
  "units": [{"id": "p01.s01", "paragraph": 1, "original": "", "revised": "",
             "changed": true, "change_types": ["grammar"], "reasons": [""],
             "protected": {"numbers": [], "citations": [], "figures": [], "hedges": []}}],
  "audit": {
    "numbers": {"ok": true, "blocking": []},
    "units": {"ok": true, "blocking": []},
    "citations": {"ok": true, "blocking": []},
    "figures": {"ok": true, "blocking": []},
    "negation": {"ok": true, "blocking": []},
    "hedging": {"ok": true, "blocking": [], "original_count": 0, "revised_count": 0},
    "terminology": {"ok": true, "violations": []}
  },
  "unresolved": [{"unit_id": "", "issue": "", "why": "", "suggested_action": ""}],
  "artifacts": [{"path": "polished.md", "kind": "markdown"},
                {"path": "changes.csv", "kind": "csv"}]
}
```

## 7. 异常处理

| 情况 | 处置 |
|---|---|
| 目标是"重写/改写"而非润色 | 明确拒绝改写主张，只做语言层；在 `unresolved` 说明 |
| 术语表内部冲突 | 以 `locked` 优先；冲突登记 `unresolved` |
| 输入含大量公式/代码 | 保护块原样保留，只改其外的自然语言 |
| 编码混乱/中英混排 | 先判主语言；非主语言段落只做格式修正 |
| 超长文本 | 按章节分批，先落盘 `partial`，再续 |

## 8. 目录

```
SKILL.md                      本文件
environment/resources.yaml    资源清单
rules/style_guide.md          按文体的语域与句式规则
rules/hedging_lexicon.csv     限定词强度表（低/中/高）
rules/edit_taxonomy.md        修改类型定义与判定口径
scripts/segment_sentences.py  分段/分句 + 保护块识别
scripts/build_terms.py        术语候选与术语表合并
scripts/audit_edits.py        守恒核查（数字/单位/引用/图表/否定/限定/术语）
scripts/make_result.py        合成 result.json + polished.md + changes.csv
templates/result.schema.json  输出结构
examples/                     最小示例（示意输出，非正式答案）
```
