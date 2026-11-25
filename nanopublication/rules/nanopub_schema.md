# Nanopublication 字段与判定口径

## 断言（assertion）

| 字段 | 含义 | 要求 |
|---|---|---|
| `text` | 断言正文 | 单一、可判定真假；含主语（或已回填指代） |
| `type` | `finding` / `method` / `limitation` / `claim` | 按线索词判定：数值/比较→finding；we used→method；only/not tested→limitation；其余→claim |
| `conditions` | 条件限定 | in/under/when/at/for 开头的短语，最多 3 条 |
| `quantifiers` | 绝对数量词 | all/always/never/every/each/none |
| `hedges` | 限定词 | may/might/could/suggest/appears/likely/partly |

## 证据（evidence）

- `kind`：`direct`（原文直述，score ≥ 0.6）/ `inferred`（0.35~0.6，需推理）/ `weak`（< 0.35）
- `anchor`：段落号 `pNNN`；`page`：页码
- **最小充分**：优先选择"能覆盖断言全部关键词且最短"的句子；
  断言含数值时，证据句必须包含同样的数值（`numbers_preserved`）

## 来源（provenance）

必备：`title`、`year`、`authors`、`source_file`。
可选：`doi`、`version`。
缺任一必备项 → `missing_source`（阻断）。

## 状态机

```
ok              全部检查通过
overbroad       含绝对数量词且无条件限定
weak_evidence   证据分数 < 0.35
duplicate       与已有断言 Jaccard > 0.9
missing_source  来源元数据不全
ambiguous_subject 主语无法回填（this/these）
```

## 质量判定

| 检查 | 触发条件 | 处置 |
|---|---|---|
| 过宽 | quantifiers 非空 且 conditions 为空 | 补条件或改限定表述 |
| 证据不足 | score < 0.35 | 换证据句或降级为 inferred 并标注 |
| 数值不一致 | 断言数字未出现在证据句 | 回原文核对 |
| 重复 | Jaccard > 0.9 | 合并 |
| 主体不一致 | 断言首词不在证据句 | 人工确认指代 |
