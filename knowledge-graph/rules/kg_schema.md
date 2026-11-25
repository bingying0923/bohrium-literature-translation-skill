# 知识图谱字段与判定口径

## 实体类型

| 类型 | 说明 | 示例 |
|---|---|---|
| `method` | 方法/仪器/模型 | colorimetric sensor、ICP-MS、calibration curve |
| `material` | 材料/试剂/器件 | chelating membrane、nanoparticle |
| `metric` | 指标 | limit of detection、recovery、RSD |
| `task` | 任务 | detection of lead ions、screening |
| `finding` | 结论句 | "recovery ranged from 92% to 108%" |

**只抽原文真实出现的 surface**；模型常识补全的概念不抽。
每个实体必须带 `anchor`（段落号）与 `evidence`（所在句）。

## 关系类型

| 类型 | 触发 | 方向 |
|---|---|---|
| `uses` | uses/used/based on/relies on | 使用者 → 被使用 |
| `measures` | measures/quantified/detected | 方法 → 对象 |
| `outperforms` | lower/higher/better than | 主语 → 比较对象 |
| `reports` | reported/achieved/ranged from | 方法 → 指标 |
| `limitation_of` | only/not tested/limited to | 被限对象 → 关联对象 |

**证据强度**：`direct`（单句 ≤180 字符且实体同句出现）/ `weak`（长句或需跨句推断）。

## 归一与消歧

- 归一键：`type + lower(去连字符/空格/复数)`
- 合并要求：同类型 + 归一键相同 → 合并，记录 `aliases` 与 `merge_reason`
- **同名不同类**（如 "sensor" 既是 method 又出现在 material 语境）→ 不合并，标 `ambiguous`
- 缩写展开：首次出现括号定义（`limit of detection (LOD)`）视为同一实体

## 查询

1. `methods_used`：方法节点 + 相关边证据
2. `metric_values`：指标节点 + `reports` 边的证据句（含数值与单位）
3. `conflicts`：同一实体对出现互相矛盾的关系类型

查询结果必须能回到 `anchor`；查不到就返回空数组并在 `unresolved` 说明。
