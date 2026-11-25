---
name: intro-related-work-writer
description: 写"引言 + 相关工作"，并逐条校验：背景是否指向真实脉络、相关工作是否按维度分组比较、研究空白是否由已引文献推出、每条贡献能否对应正文证据、引用是否覆盖且与论断一一对应。输出可编辑的引言稿 + 引用-论断映射表 + 问题清单。当用户要求写引言/相关工作/研究背景/贡献陈述，或检查"引用与论断是否对得上"时使用。
version: 1.0.0
---

# 引言与相关工作：立得住 + 分得清 + 对得上

写引言不是堆"近年来受到广泛关注"，而是**用已引文献推出一个具体缺口**，再把本文贡献逐条钉到证据上。

**不做什么**：不编造文献、不写没有出处的"众所周知"、不把综述转述当本研究结果。

## 1. 适用条件

- 已有：事实底稿（本文方法与结果）、文献清单（含元数据）、目标期刊/会议风格
- 需要：引言与相关工作成稿 + 可核对的引用映射
- 不适用：没有任何文献可引（应先补检索）

## 2. 输入

| 来源 | 说明 |
|---|---|
| `/input/case.json` | `case_id`、主题、目标文体 |
| `facts.json` | 本文事实：方法要点、关键数值、图表编号、贡献候选 |
| `refs.json` / `.bib` | 文献清单：作者、年份、题名、DOI |

## 3. 输出（必须）

`/app/output/result.json` + `/app/output/intro.md` + `/app/output/citation_map.csv`

## 4. 执行流程

### Step 1 搭骨架（4 段式）

```bash
python3 scripts/build_outline.py --facts facts.json --refs refs.json --out work/outline.json
```

| 段落 | 写什么 | 硬要求 |
|---|---|---|
| 背景 | 领域脉络 → 具体问题 → 技术约束 | 每句带引用，或标 `[author-claim]` |
| 相关工作 | 按**维度**分组（问题设定/方法路线/数据与评价） | 每组 ≥2 篇，且同维度比较取舍 |
| 研究空白 | 由已引工作的共同限制推出 | 必须能指回被引文献的具体限制 |
| 本文贡献 | 3~4 条，逐条对应方法/图表/结果 | 每条给 `evidence`（图号/表号/数值） |

### Step 2 写稿

按 outline 写，规则见 `rules/writing_rules.md`：
- 禁止空转句（"近年来…广泛关注""具有重要意义"）
- 相关工作**不按时间罗列**，按维度分组；每组给出"共同限制"
- 贡献条目必须可核对：`我们提出 X（Fig. 2），在 Y 上达到 Z`

### Step 3 校验

```bash
python3 scripts/check_intro.py --intro work/intro.json --refs refs.json \
    --facts facts.json --out work/check.json
```

| 检查 | 判据 | 不通过 |
|---|---|---|
| 引用覆盖 | 背景/相关工作段落里 ≥90% 句子含引用或 `[author-claim]` | 列出未标注句 |
| 空转句 | 命中 "widely studied/received much attention/具有重要意义" 等 | 要求改写 |
| 分组维度 | 相关工作至少 2 组，每组 ≥2 引用 | 补分组 |
| 空白推导 | 空白句必须引用 ≥1 篇"被限制"的文献 | 补引用或改措辞 |
| 贡献可核对 | 每条贡献含 `evidence`（Fig./Table/数值） | 补证据或降级表述 |
| 引用有效性 | 引用 key 都在 refs 中；refs 中未引用的列 `uncited` | 补引或删条目 |

### Step 4 产出

```bash
python3 scripts/make_result.py --case-json /input/case.json --intro work/intro.json \
    --check work/check.json --out /app/output/result.json
```

## 5. 状态与诚实性

- `status`：`success`（校验全过）/ `partial`（有未标注句或贡献缺证据）/ `failed` / `stuck`
- `issues` 写清：哪一句、哪条贡献、缺什么
- 禁止：为凑引用而堆砌不相关文献；把"可能"写成"证明"；贡献超出实验范围

## 6. result.json 契约

```json
{
  "case_id": "",
  "status": "success|partial|failed|stuck",
  "outline": {"background": [], "related_work": [{"group": "", "refs": [], "limitation": ""}],
              "gap": {"text": "", "refs": []}, "contributions": [{"text": "", "evidence": ""}]},
  "intro": {"paragraphs": [{"id": "p1", "role": "background|related|gap|contributions",
                             "text": "", "citations": []}]},
  "citation_map": [{"sentence_id": "", "claims": "", "refs": []}],
  "checks": {"coverage": {"ok": true, "issues": []}, "empty_phrases": {"ok": true, "issues": []},
             "grouping": {"ok": true, "issues": []}, "gap_support": {"ok": true, "issues": []},
             "contributions": {"ok": true, "issues": []}, "refs_valid": {"ok": true, "uncited": []}},
  "issues": [{"where": "", "issue": "", "suggested_action": ""}],
  "artifacts": [{"path": "intro.md", "kind": "markdown"}, {"path": "citation_map.csv", "kind": "csv"}]
}
```

## 7. 异常处理

| 情况 | 处置 |
|---|---|
| 文献不足 3 篇 | `partial`，说明"相关工作无法分组" |
| 贡献无法对应证据 | 改写成"我们设想/后续将验证"，或删除 |
| 引用格式不一 | 统一为 `[n]` 或 `(Author, Year)`，记入 issues |
| 主题与文献不匹配 | `failed`，说明不匹配 |
| 空白推导缺依据 | 不写空白句，改为"尚未见报道（截至检索日期）" |

## 8. 目录

```
SKILL.md                      本文件
environment/resources.yaml    资源清单
rules/writing_rules.md        句式、禁用语、分组与贡献写法
scripts/build_outline.py      从事实与文献生成 4 段式骨架
scripts/check_intro.py        覆盖/空转/分组/空白/贡献/引用 六项校验
scripts/make_result.py        合成 result.json + intro.md + citation_map.csv
templates/result.schema.json  输出结构
examples/                     最小示例（示意输出）
```
