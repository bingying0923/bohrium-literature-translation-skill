---
name: paper-notes-section-aligned
description: 把一篇科研论文整理成"章节对齐 + 字段化 + 锚点可回溯"的结构化笔记：按 Abstract/Introduction/Methods/Results/Discussion 逐节提炼，生成论文卡片（研究问题、数据、方法、主要发现、局限），每条笔记都带原文锚点（页/段/句），并自动检查覆盖度、数字来源与无依据断言。当用户要求做文献笔记、论文卡片、章节摘要、文献综述素材、知识点清单时使用。
version: 1.0.0
---

# 文献总结与结构化笔记：章节对齐 + 锚点回链

把论文变成**能并排比较、能点回原文**的笔记，而不是一段压缩摘要。

**不做什么**：不写"通读摘要"、不加原文没有的结论、不把讨论段的推测写成结果段的事实。

## 1. 适用条件

- 输入是一篇完整论文或其章节（PDF 文本 / Markdown / 纯文本）
- 读者需要"结构化复用"：同一领域的多篇论文能按字段并排比较
- 不适用于：只有摘要没有正文（字段会大量缺失，应标 `partial`）

## 2. 输入

| 来源 | 说明 |
|---|---|
| `/input/case.json` | `case_id`、材料路径、领域、是否需要论文卡片 |
| `/input/*.md`、`*.txt` | 论文文本；页边界用 `[page N]` 或换页符 |
| 字段字典（可选） | 自定义论文卡片字段；默认用 `rules/field_schema.md` |

## 3. 输出（必须）

`/app/output/result.json`（契约见 §6），另有：

- `/app/output/notes.md`：按章节组织的阅读笔记（每条带锚点）
- `/app/output/paper_card.json`：字段化论文卡片（同领域可并排比较）

## 4. 执行流程

### Step 0 读要求

确认：领域、目标读者、是否要论文卡片、锚点粒度（页/段/句）。写进 `work/plan.json`。

### Step 1 章节切分与锚点

```bash
python3 scripts/segment_sections.py --input input.md --out work/sections.json
```

- 识别 Abstract / Introduction / Related Work / Methods / Results / Discussion / Conclusion / Limitations
- 每个段落给稳定锚点：`p012`（页 `pg3`），句子给 `p012.s2`
- 页眉页脚、页码行自动剔除；参考文献单独成节，不进入笔记正文

### Step 2 字段抽取（论文卡片）

```bash
python3 scripts/extract_fields.py --sections work/sections.json --out work/card.json
```

按 `rules/field_schema.md` 抽 7 个字段，**每个字段必须带锚点列表**：

| 字段 | 抽取线索 | 缺失时 |
|---|---|---|
| `research_question` | "we ask/aim/investigate/hypothesize" | 标 `not_reported` |
| `data` | 样本量、数据集名、地点、时间范围 | 标 `not_reported` |
| `methods` | 方法名、设备、参数、统计方法 | 标 `not_reported` |
| `key_findings` | 结果段中含数字/比较级的句子 | 标 `not_reported` |
| `limitations` | "limitation/caveat/future work/only" | 标 `not_reported` |
| `novelty` | "first/unlike/previous studies" | 标 `not_reported` |
| `terms` | 领域术语（供跨篇对齐） | 空列表 |

### Step 3 章节笔记

按章节逐段提炼 1~3 条笔记，每条形如：

```
[Methods] 采用 36 份水样、三城市采样，检出限 0.8 µg/L。 (p012, pg3)
```

规则：
- 一句话说清"这一段做了什么/发现了什么"，**保留数字与限定词**
- 每条必须挂锚点；无法确定锚点的句子不写进笔记
- Discussion 的推测必须带 "作者推测" 前缀，不得写成结论

### Step 4 质量检查（决定"可核验"）

```bash
python3 scripts/check_notes.py --sections work/sections.json --notes work/notes.json \
    --card work/card.json --out work/check.json
```

检查项：

| 检查 | 判据 | 不通过 |
|---|---|---|
| 覆盖度 | 每个非空章节至少 1 条笔记 | `partial`，列出未覆盖章节 |
| 锚点有效 | 每条笔记的锚点存在于原文章节 | 删除该条或补锚点 |
| 数字溯源 | 笔记中每个数字能在对应锚点原文中找到 | 标 `number_unverified` |
| 无新增事实 | 笔记中出现原文没有的因果词/比较词要标记 | 人工确认 |
| 局限必填 | 论文有限制段就必须有 `limitations` | 标 `not_reported` 并说明 |

### Step 5 产出

```bash
python3 scripts/make_result.py --case-json /input/case.json --sections work/sections.json \
    --notes work/notes.json --card work/card.json --check work/check.json \
    --out /app/output/result.json
```

生成 `result.json`、`notes.md`、`paper_card.json`。

## 5. 状态与诚实性

- `status`：`success`（所有章节覆盖、检查通过）/ `partial`（有未覆盖章节或数字未溯源）/ `failed` / `stuck`
- `not_reported` 是合法值，**不要用推测填空**
- `uncertainties` 每条写 `anchor`、`issue`、`why`、`suggested_action`

## 6. result.json 契约

```json
{
  "case_id": "",
  "status": "success|partial|failed|stuck",
  "paper": {"title": "", "pages": 0, "sections": ["Abstract", "Methods"]},
  "card": {
    "research_question": {"value": "", "anchors": ["p001"], "status": "reported|not_reported"},
    "data": {"value": "", "anchors": [], "status": ""},
    "methods": {"value": "", "anchors": [], "status": ""},
    "key_findings": [{"value": "", "anchors": [], "numbers": []}],
    "limitations": {"value": "", "anchors": [], "status": ""},
    "novelty": {"value": "", "anchors": [], "status": ""},
    "terms": []
  },
  "notes": [{"section": "Methods", "anchor": "p012", "page": 3, "text": "", "kind": "method|result|claim|limitation"}],
  "coverage": {"sections_total": 0, "sections_covered": 0, "missing": []},
  "checks": {
    "anchors": {"ok": true, "issues": []},
    "numbers": {"ok": true, "issues": []},
    "no_new_facts": {"ok": true, "issues": []},
    "limitations": {"ok": true, "issues": []}
  },
  "unresolved": [{"anchor": "", "issue": "", "why": "", "suggested_action": ""}],
  "artifacts": [{"path": "notes.md", "kind": "markdown"},
                {"path": "paper_card.json", "kind": "json"}]
}
```

## 7. 异常处理

| 情况 | 处置 |
|---|---|
| 只有摘要 | 字段大面积 `not_reported`，`status=partial`，说明"仅有摘要" |
| 无限制段 | `limitations.status=not_reported`，并在 `unresolved` 说明"原文未单列" |
| 章节识别失败 | 退化为"按段落编号"的组织方式，仍给锚点 |
| 公式/表格为主 | 只记录位置与题注，不臆造数值 |
| 图文混排丢失 | 标 `partial`，列出无法解析页 |

## 8. 目录

```
SKILL.md                        本文件
environment/resources.yaml      资源清单
rules/field_schema.md           论文卡片字段字典与判定口径
rules/note_style.md             笔记写法与锚点格式
scripts/segment_sections.py     章节切分 + 锚点
scripts/extract_fields.py       卡片字段抽取
scripts/check_notes.py          覆盖度/锚点/数字/新增事实核查
scripts/make_result.py          合成 result.json + notes.md + paper_card.json
templates/result.schema.json    输出结构
examples/                       最小示例（示意输出）
```
