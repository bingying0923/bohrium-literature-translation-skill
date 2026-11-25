---
name: methods-experiments-writer
description: 把零散实验记录整理成可复现的"方法与实验"章节：有序步骤（含输入/操作/输出/判断条件）、参数表（名称/取值/单位/作用对象/来源）、数据集与划分、对照与重复次数、复现清单，并校验参数与日志/配置是否一致、有无凭空补出的数值。当用户要求写 Methods/实验设置、整理参数表、补复现清单或检查"参数与日志对不对得上"时使用。
version: 1.0.0
---

# 方法与实验章节：写得全 + 写得准 + 做得着

把实验记录变成**别人照着能复做**的章节，参数逐个带来源，缺口显式标出。

**不做什么**：不为段落顺滑补数值；不把训练/验证条件混写；不承诺未经验证的复现性。

## 1. 适用条件

- 输入：实验记录、配置、日志、数据说明（结构化或半结构化）
- 需要：方法步骤、参数表、数据集划分、对照与重复、复现清单
- 不适用：只有结论没有过程记录（应先补记录）

## 2. 输入

| 来源 | 说明 |
|---|---|
| `/input/case.json` | `case_id`、章节范围 |
| `protocol.md` | 步骤（编号列表）、参数表、数据集说明 |
| `config.json` / `run.log` | 参数与运行条件的原始来源（用于核对） |

## 3. 输出（必须）

`/app/output/result.json` + `/app/output/methods.md`

## 4. 执行流程

### Step 1 解析记录

```bash
python3 scripts/parse_protocol.py --protocol protocol.md [--config config.json] --out work/parsed.json
```

- 步骤：编号列表 → `{n, text, input, output, condition}`
- 参数：表格行 → `{name, value, unit, target, source}`
- 数据集：`name/version/n/split/preprocess/use`
- 有 config 时，用 config 校正参数的 `value` 与 `source`

### Step 2 写章节

结构（顺序固定）：

1. 材料与数据（数据集名、版本、规模、预处理、划分比例与随机方式）
2. 实验设置（硬件、软件版本、运行环境、随机种子、重复次数）
3. 方法步骤（有序、每步输入/操作/输出/判断）
4. 对照与评价（基线对象及版本、是否同预算、指标与统计方式）
5. 复现清单（代码版本、环境、命令、数据获取）
6. 限制条件（具体失效场景）

写作规则见 `rules/methods_rules.md`。

### Step 3 校验

```bash
python3 scripts/check_methods.py --parsed work/parsed.json --draft work/draft.json \
    --config config.json --out work/check.json
```

| 检查 | 判据 | 不通过 |
|---|---|---|
| 步骤完整 | 每步有 input 与 output | 补全或标注"记录缺失" |
| 参数可追溯 | 每个参数有 unit + source | 补来源或标 `unverified` |
| 数值一致 | 正文数值 = 参数表数值 = 日志数值 | 以日志为准回改 |
| 数据集完整 | 有 name/version/n/split | 缺项标 `missing` |
| 复现要素 | 有 seed、软件版本、命令 | 补或标 `not_recorded` |
| 对照可比 | 基线有版本、同预算声明 | 补声明或降级表述 |
| 限制具体 | 限制指向失效场景，不是套话 | 改写 |

### Step 4 产出

```bash
python3 scripts/make_result.py --case-json /input/case.json --parsed work/parsed.json \
    --check work/check.json --out /app/output/result.json
```

## 5. 状态与诚实性

- `status`：`success` / `partial`（有 missing / unverified）/ `failed` / `stuck`
- 缺记录就写 `not_recorded`，**不要编数值**
- `issues` 写清：哪个参数/步骤、缺什么、影响哪条复现路径

## 6. result.json 契约

```json
{
  "case_id": "",
  "status": "success|partial|failed|stuck",
  "steps": [{"n": 1, "text": "", "input": "", "output": "", "condition": ""}],
  "params": [{"name": "", "value": "", "unit": "", "target": "", "source": "config|log|author", "verified": true}],
  "datasets": [{"name": "", "version": "", "n": 0, "split": "", "preprocess": "", "use": ""}],
  "reproduce": {"code_version": "", "env": "", "command": "", "seed": "", "repeats": 0},
  "checks": {"steps": {"ok": true, "issues": []}, "params": {"ok": true, "issues": []},
             "numbers": {"ok": true, "issues": []}, "datasets": {"ok": true, "issues": []},
             "reproduce": {"ok": true, "issues": []}, "baseline": {"ok": true, "issues": []},
             "limitations": {"ok": true, "issues": []}},
  "issues": [{"where": "", "issue": "", "suggested_action": ""}],
  "artifacts": [{"path": "methods.md", "kind": "markdown"}]
}
```

## 7. 异常处理

| 情况 | 处置 |
|---|---|
| 参数缺来源 | `verified=false` + `unverified`，不写进正文数值 |
| 日志与配置冲突 | 以日志为准，`issues` 记录冲突项 |
| 数据集版本不明 | 标 `version=unknown`，说明"版本含混会影响复现" |
| 无随机种子 | `seed=not_recorded`，说明"结果不可逐位复现" |
| 对照不同预算 | 明确写出，不称"优于基线" |

## 8. 目录

```
SKILL.md                      本文件
environment/resources.yaml    资源清单
rules/methods_rules.md        章节结构、参数表规范、限制写法
scripts/parse_protocol.py     步骤/参数/数据集解析与 config 校正
scripts/check_methods.py      七项完整性与一致性校验
scripts/make_result.py        合成 result.json + methods.md
templates/result.schema.json  输出结构
examples/                     最小示例（示意输出）
```
