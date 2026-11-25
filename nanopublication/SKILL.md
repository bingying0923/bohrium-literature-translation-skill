---
name: nanopublication-claims
description: 把论文段落拆成可独立判断真假的原子断言，为每条断言绑定最小证据片段与原文锚点，补齐来源元数据（论文/作者/年份/版本），并做"过宽断言、证据不足、来源缺失、重复断言"四类质量检查，导出可直接被下游程序解析的 JSON。当用户要求做 nanopublication、断言拆解、证据绑定、知识单元结构化或科研结论可追溯化时使用。
version: 1.0.0
---

# Nanopublication：断言拆解 + 证据绑定 + 来源可追溯

把"一段结论"变成"若干条各自可判定真假的断言 + 每条的原文证据 + 完整来源链"。

**不做什么**：不补造论文没写的结论；不把综述转述当直接证据；不把整段话塞进一个字段。

## 1. 适用条件

- 输入是论文正文（含结果/讨论段落）或结构化摘录
- 需要：原子断言、最小证据片段、来源元数据、机器可读导出
- 不适用：纯图表数据（需先数字化）、无原文可回查的二手段材料

## 2. 输入

| 来源 | 说明 |
|---|---|
| `/input/case.json` | `case_id`、论文元数据（标题/作者/年份/版本/DOI） |
| `/input/*.md`、`*.txt` | 论文文本；页边界 `[page N]` |

## 3. 输出（必须）

`/app/output/result.json`（契约见 §6）+ `/app/output/nanopubs.json`（条目数组）。

## 4. 执行流程

### Step 1 断言拆解（决定"拆得细"）

```bash
python3 scripts/decompose_claims.py --input paper.md --out work/claims.json
```

拆分规则：

- 先按句切分；再在 `;`、`, and`、`, but`、`, whereas`、`；` 处拆子句
- 每个子句必须**独立成句仍可判断真假**；拆完检查是否含主语（或可从上文继承的指代，需回填）
- 每条保留：限定词（may/suggest/only/部分）、数量词（all/never/each）、条件（in/under/when/at ...）
- 类型：`finding`（有数值/比较）、`method`（we used/developed）、`limitation`（only/not tested）、`claim`（推论）

### Step 2 证据绑定（决定"对得上"）

```bash
python3 scripts/bind_evidence.py --claims work/claims.json --paper paper.md --out work/bound.json
```

- 对每条断言，在原文句子里找**最小充分片段**：token 重叠最高且长度最短的连续片段
- 记录 `anchor`（段落号）、`evidence_text`、`score`（0~1）
- `score < 0.35` → 标 `weak_evidence`，进质量检查
- 区分 `direct`（原文直述）与 `inferred`（需跨句推理，默认降级为 weak）

### Step 3 质量检查（决定"追得回"）

```bash
python3 scripts/validate_nanopub.py --claims work/claims.json --bound work/bound.json \
    --meta meta.json --out work/validation.json
```

| 检查 | 判据 |
|---|---|
| 过宽断言 | 含 all/always/never/every/所有/总是 且无条件限定 → 标 `overbroad` |
| 证据不足 | score < 0.35，或证据句不含断言的关键数字/对象 |
| 来源缺失 | 缺 title/year/authors/source_file 任一项 |
| 重复断言 | 归一化文本相同或 Jaccard > 0.9 |
| 主体混淆 | 断言主语与证据句主语不一致（启发式：首名词组不同） |

### Step 4 导出

```bash
python3 scripts/make_result.py --case-json /input/case.json --claims work/claims.json \
    --bound work/bound.json --validation work/validation.json --out /app/output/result.json
```

导出结构见 §6；同时写 `nanopubs.json`（纯条目数组，便于下游直接读）。

## 5. 状态与诚实性

- `status`：`success`（无阻断问题）/ `partial`（存在 weak_evidence / overbroad / 来源缺失）/ `failed` / `stuck`
- 每条问题写清 `claim_id` + `issue` + `why` + `suggested_action`
- 禁止：把推论标成直接证据；缺元数据用占位符；一条断言挂多个不连续证据

## 6. result.json 契约

```json
{
  "case_id": "",
  "status": "success|partial|failed|stuck",
  "source": {"title": "", "authors": [], "year": "", "version": "", "doi": "", "source_file": ""},
  "stats": {"claims": 0, "with_direct_evidence": 0, "weak": 0, "overbroad": 0, "duplicates": 0},
  "nanopubs": [
    {
      "id": "np001",
      "assertion": {"text": "", "type": "finding|method|limitation|claim",
                     "conditions": [], "quantifiers": [], "hedges": []},
      "evidence": {"anchor": "p003", "text": "", "score": 0.82, "kind": "direct|inferred"},
      "provenance": {"title": "", "authors": [], "year": "", "doi": "", "source_file": ""},
      "status": "ok|weak_evidence|overbroad|missing_source|duplicate"
    }
  ],
  "issues": [{"claim_id": "", "issue": "", "why": "", "suggested_action": ""}],
  "artifacts": [{"path": "nanopubs.json", "kind": "json"}]
}
```

## 7. 异常处理

| 情况 | 处置 |
|---|---|
| 段落里全是引用转述 | 标记 `inferred`，降低 score，不冒充直接证据 |
| 断言主语是 this/these | 回填最近的前文主语；无法回填则标 `ambiguous_subject` |
| 原文含公式/表格 | 只引用题注与上下文，不解析数值 |
| 元数据缺失 | `missing_source`，不编造作者与年份 |
| 重复段落 | 归一化后去重，保留首次锚点 |

## 8. 目录

```
SKILL.md                       本文件
environment/resources.yaml     资源清单
rules/nanopub_schema.md        字段定义、状态机与质量判定口径
scripts/decompose_claims.py    句子/子句拆分与断言分类
scripts/bind_evidence.py       最小证据片段匹配与打分
scripts/validate_nanopub.py    过宽/证据/来源/重复/主体 五项检查
scripts/make_result.py         合成 result.json + nanopubs.json
templates/result.schema.json   输出结构
examples/                      最小示例（示意输出）
```
