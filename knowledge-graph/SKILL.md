---
name: literature-knowledge-graph
description: 从论文中抽取科研实体（方法、材料、指标、任务、结论）与有证据支撑的关系，做别名归一与同名消歧，导出可查询的节点/边 JSON，并支持三个真实查询（方法清单、指标取值、冲突关系）与证据回链。当任务要求构建文献知识图谱、抽取实体关系、做来源绑定或回答图谱查询时使用。
version: 1.0.0
---

# 文献知识图谱：抽得准 + 连得对 + 回得去

从论文里抠出**真实出现的**科研对象和**有证据的**关系，导出可查询的图，而不是凭常识补全概念。

**不做什么**：不凭领域常识补实体；不把"同时出现"当关系；不合并同名但不同实体。

## 1. 适用条件

- 输入是一篇（或几篇）论文文本，围绕一个明确主题
- 需要：实体清单、关系三元组、证据锚点、基本查询
- 不适用：纯表格数据抽取（需先数字化）、跨语言大规模对齐

## 2. 输入

| 来源 | 说明 |
|---|---|
| `/input/case.json` | `case_id`、论文元数据、主题 |
| `/input/*.md`、`*.txt` | 论文文本（多篇用 `[paper N]` 分隔） |

## 3. 输出（必须）

`/app/output/result.json`（契约见 §6）+ `/app/output/graph.json`（`{nodes, edges}`）+ `/app/output/queries.json`。

## 4. 执行流程

### Step 1 实体抽取

```bash
python3 scripts/extract_entities.py --input paper.md --out work/entities.json
```

- 类型：`method`（传感器/色谱/质谱/模型）、`material`（膜、纳米颗粒、试剂）、
  `metric`（检出限、回收率、RSD、AUC）、`task`（检测/分类/预测）、`finding`（结论句）
- 每个实体保留：`surface`（原文写法）、`anchor`、`page`、`sentence`
- 只抽**原文真实出现**的名词短语；模型常识补全的概念一律不抽

### Step 2 关系抽取

```bash
python3 scripts/extract_relations.py --entities work/entities.json --input paper.md --out work/relations.json
```

| 关系 | 触发模式 | 方向 |
|---|---|---|
| `uses` | X uses/employs/based on Y | X → Y |
| `measures` | X measures/quantifies Y | X → Y |
| `outperforms` | X is lower/higher than Y；X outperforms Y | 依据比较词定方向 |
| `reports` | X reported/achieved Y（Y 为指标值） | X → Y |
| `limitation_of` | only/not tested/limited to | 结论 → 方法 |

- 每条边必须带 `evidence`（原文句 + 锚点）与 `strength`（`direct` / `weak`）
- 同一对实体多个关系保留多个类型，不合并

### Step 3 归一与消歧

- 别名归一：全称/缩写（首次出现括号定义）、大小写、连字符、单复数
- 同名消歧：同名但上下文不同的实体**不合并**，标 `ambiguous`，列候选
- 合并需给出 `merge_reason`（如 "LOD = limit of detection，由首次出现括号定义"）

### Step 4 图与查询

```bash
python3 scripts/make_result.py --case-json /input/case.json --entities work/entities.json \
    --relations work/relations.json --out /app/output/result.json
```

内置三个查询（写进 `queries.json`）：

1. `methods_used`：本文用了哪些方法，各自证据在哪
2. `metric_values`：某指标的报告值（含单位）与出处
3. `conflicts`：同一实体对上的矛盾关系（如同时 outperforms 与 worse）

### Step 5 自检

1. 每个节点都能回到原文句；每条边都有证据
2. 没有"凭常识"出现的实体（抽出的 surface 必须在原文出现）
3. 别名合并都写了依据；同名未合并的已标 `ambiguous`
4. 三个查询都能返回非空结果或明确说明"图中无此信息"

## 5. 状态与诚实性

- `status`：`success` / `partial`（有 weak 边或 ambiguous 实体）/ `failed` / `stuck`
- `unresolved` 写：缺证据的边、歧义实体、无法回答的查询
- 禁止：把共现当关系、把综述转述当直接证据、合并未确认的同名实体

## 6. result.json 契约

```json
{
  "case_id": "",
  "status": "success|partial|failed|stuck",
  "topic": "",
  "stats": {"nodes": 0, "edges": 0, "direct_edges": 0, "weak_edges": 0, "ambiguous": 0},
  "nodes": [{"id": "n001", "type": "method|material|metric|task|finding",
             "surface": "", "canonical": "", "aliases": [], "anchor": "p003",
             "page": 1, "evidence": "", "ambiguous": false}],
  "edges": [{"id": "e001", "source": "n001", "target": "n002", "type": "uses|measures|outperforms|reports|limitation_of",
             "direction": "forward|reverse", "evidence": "", "anchor": "p004", "strength": "direct|weak"}],
  "queries": [{"q": "methods_used", "answer": [{"node": "", "evidence": ""}], "note": ""}],
  "unresolved": [{"issue": "", "why": "", "suggested_action": ""}],
  "artifacts": [{"path": "graph.json", "kind": "json"}, {"path": "queries.json", "kind": "json"}]
}
```

## 7. 异常处理

| 情况 | 处置 |
|---|---|
| 实体只在图表里出现 | 记 `unresolved`，不凭空造节点 |
| 关系由多句拼接 | `strength=weak`，并在 unresolved 说明 |
| 同名不同物 | 不合并，标 `ambiguous` + 候选 |
| 跨论文冲突结论 | 两条边都保留，查询 `conflicts` 返回 |
| 主题与论文不符 | `failed`，说明"材料与主题不匹配" |

## 8. 目录

```
SKILL.md                       本文件
environment/resources.yaml     资源清单
rules/kg_schema.md             实体/关系类型、归一与消歧规则
scripts/extract_entities.py    实体抽取（带锚点）
scripts/extract_relations.py   关系抽取（模式 + 方向 + 强度）
scripts/make_result.py         归一/去重/建图/三个查询/导出
templates/result.schema.json   输出结构
examples/                      最小示例（示意输出）
```
