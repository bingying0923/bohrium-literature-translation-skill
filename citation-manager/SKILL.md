---
name: citation-consistency-manager
description: 管理正文引用与文末参考文献的一致性：解析 [n]/[n-m] 与 (Author, Year) 标记、拆分参考文献字段、按首次出现顺序重排编号、合并重复条目、检查缺引/多引/缺号/字段残缺，并输出可直接用的稿件与文献表。当用户要求整理参考文献、统一引用格式、更新编号、去重、核对正文引用与文献列表是否对应时使用。
version: 1.0.0
---

# 参考文献与引用管理：挂得对 + 编得顺 + 收得净

把"正文引用 ↔ 文末列表"理成一套**编号连续、条目唯一、可回溯**的体系，并留下改动记录。

**不做什么**：不替作者决定"哪句需要引用"（这属于学术判断），不编造文献信息，不擅自改作者名/年份/DOI。

## 1. 适用条件

- 输入是一份含正文引用的稿件 + 文末参考文献列表（Markdown/纯文本）
- 需要：编号重排、去重、一致性核查、格式统一
- 不适用：需要从零补文献（缺文献信息时应报告，不猜）

## 2. 输入

| 来源 | 说明 |
|---|---|
| `/input/case.json` | `case_id`、稿件路径、目标引用样式（numeric / author-year） |
| `/input/*.md`、`*.txt` | 含正文与 `References/参考文献` 段落的稿件 |

## 3. 输出（必须）

`/app/output/result.json`（契约见 §6），另有：

- `/app/output/manuscript.md`：重排后的稿件（正文 + 统一编号的文献表）
- `/app/output/references.json`：结构化文献条目（authors/year/title/venue/doi）
- `/app/output/citation_changes.csv`：旧编号 → 新编号映射

## 4. 执行流程

### Step 1 解析

```bash
python3 scripts/parse_refs.py --input manuscript.md --out work/refs.json
```

- 正文标记：`[1]`、`[2-4]`、`[1,3]`、`(Smith et al., 2020)`
- 文献列表：以 `[n]`/`n.` 开头的条目，支持续行拼接
- 字段：作者、年份、题名、出处、DOI；题名优先取引号内文本，否则取第二个句段
- 输出引用锚点 `pNNN`（按正文段落计）

### Step 2 一致性核查

```bash
python3 scripts/audit_citations.py --refs work/refs.json --out work/audit.json
```

| 检查 | 判据 | 处理 |
|---|---|---|
| 缺引 | 正文引了但列表没有 | 阻断，补文献或删引用 |
| 多引 | 列表有但正文从未引用 | 阻断，补引或删条目 |
| 缺号 | 编号不连续 | 重排 |
| 顺序 | 首次出现顺序 ≠ 编号顺序 | 重排 |
| 重复 | DOI 或题名或作者+年份相同 | 合并到最早编号 |
| 字段残缺 | 缺作者/年份/题名 | 阻断，补全后再提交 |
| 样式混用 | 数字制与著者年制混用 | 提示统一 |

### Step 3 重排与去重

```bash
python3 scripts/renumber.py --refs work/refs.json --out work/revised.json
```

- 顺序：按正文首次出现；未被引用的条目排在最后（并保留"多引"告警）
- 编号：连续 1..N
- 重复：同一 DOI/题名归到最早编号，正文标记一并合并
- 合并后条目数减少时，编号仍然连续（不出现空号）

### Step 4 产出

```bash
python3 scripts/make_result.py --case-json /input/case.json \
    --refs work/refs.json --revised work/revised.json --audit work/audit.json \
    --out /app/output/result.json
```

### Step 5 自检

1. 正文每个 `[n]` 都能在列表里找到；列表每条都被引用（或已说明为何保留）
2. 编号 1..N 连续、无空号
3. 无重复条目（DOI/题名归一后唯一）
4. 每条都有作者、年份、题名
5. `citation_changes.csv` 与实际正文改动一致

## 5. 状态与诚实性

- `status`：`success`（无阻断项）/ `partial`（有缺引/多引/缺字段，已列 todo）/ `failed` / `stuck`
- `todo` 每条写：问题 + 建议动作（补文献、补引、删条目、统一样式）
- 禁止：为了让编号连续而删除真实文献、把缺失字段用占位符糊过去

## 6. result.json 契约

```json
{
  "case_id": "",
  "status": "success|partial|failed|stuck",
  "style": "numeric|author-year|unknown",
  "manuscript": {"body": "", "citations_in_text": 0, "references": 0},
  "references": [{"index": 1, "old_index": 3, "authors": "", "year": "2021",
                  "title": "", "venue": "", "doi": "", "raw": ""}],
  "audit": {
    "missing_references": [], "uncited_references": [], "numbering_gaps": [],
    "order_of_appearance_ok": true, "first_appearance_order": [],
    "duplicates": [], "incomplete_entries": [], "style_mixed": {}
  },
  "changes": {"renumber_mapping": {}, "merged_duplicates": {}, "markers_updated": 0},
  "todo": [{"issue": "", "suggested_action": ""}],
  "artifacts": [{"path": "manuscript.md", "kind": "markdown"},
                {"path": "references.json", "kind": "json"},
                {"path": "citation_changes.csv", "kind": "csv"}]
}
```

## 7. 异常处理

| 情况 | 处置 |
|---|---|
| 没有 References 段 | `failed`，说明"未找到文献列表" |
| 条目缺 DOI/题名 | 记入 `incomplete_entries`，不猜 |
| 数字制与著者年制混用 | 记 `style_mixed`，按目标样式统一后再重排 |
| 引用指向不存在的编号 | 记 `missing_references`，保留原编号不擅改 |
| 重复条目信息不一致 | 保留信息更全者，另一条记入 `changes` |
| 参考文献跨页断行 | 续行拼接；仍不完整则标记待人工核对 |

## 8. 目录

```
SKILL.md                        本文件
environment/resources.yaml      资源清单
rules/citation_rules.md         编号/去重/字段判定口径
scripts/parse_refs.py           正文引用与文献条目解析
scripts/audit_citations.py      一致性、顺序、缺号、重复、字段核查
scripts/renumber.py             按首次出现重排 + 去重合并
scripts/make_result.py          合成 result.json + manuscript.md + references.json
templates/result.schema.json    输出结构
examples/                       最小示例（示意输出）
```
