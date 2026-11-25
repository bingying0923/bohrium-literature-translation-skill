# 论文卡片字段字典

每个字段都必须给出 `value`、`anchors`、`status`。`status` 取值：

- `reported`：原文明确写了
- `not_reported`：原文没写（**不要用推测填充**）

| 字段 | 含义 | 抽取位置 | 判定口径 | 常见错误 |
|---|---|---|---|---|
| `research_question` | 研究问题/目标 | Abstract、Introduction 末段 | 出现 aim/goal/objective/investigate/ask/hypothesize 且指向"要解决什么" | 把方法当问题 |
| `data` | 数据来源与规模 | Methods、Abstract | 样本量、数据集名、地点、时间窗、纳排标准 | 漏掉 n=，只写"临床样本" |
| `methods` | 方法与关键参数 | Methods | 方法名 + 关键条件（温度、时长、仪器、统计） | 只写"我们做了实验" |
| `key_findings` | 主要发现 | Results、Abstract | 含数值/比较/统计显著性的结果句 | 把讨论里的推测当发现 |
| `limitations` | 局限与边界 | Discussion、Limitations、Conclusion | limitation/caveat/only/future work/尚未验证 | 与"未来工作"混淆 |
| `novelty` | 新意 | Introduction、Discussion | first/unlike previous/novel | 自夸式表述照抄 |
| `terms` | 领域术语 | 全文 | 名词短语、缩写、带连字符术语 | 抽到 "The/This" |

## 锚点约定

- 段落锚点：`p012`（全局段落序号，三位补零）
- 句子锚点：`p012.s3`（第 3 句）
- 页号：`page`，来自 `[page N]` 标记或换页符

## 比较可比性

同一领域的多篇论文，`data`/`methods`/`key_findings` 三个字段必须能**并排比较**：
数值带单位、条件带范围、发现带方向（increase/decrease/no change）。
