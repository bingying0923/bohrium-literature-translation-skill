# Bohrium 校园挑战赛 · 北京化工大学分站赛 — 参赛作品集

本仓库收录参加 **Bohrium Science Space 校园挑战赛（北京化工大学分站赛，第一期）** 的 10 个 Skill 作品。
每个作品都是可被 Agent 直接调用的技能包：`SKILL.md`（含 YAML 元信息）+ 脚本 + 规则表 + 示例。

## 一期十题

| # | 赛题 | 目录 | 核心能力 |
|---|---|---|---|
| 1 | 文献文档解析 | [`pdf-parser/`](pdf-parser/) | 逐页双栏重排、去页眉页脚、表格转 Markdown、章节树与题注/公式定位 |
| 2 | 文献翻译 | 仓库根目录 | 术语锁定的双语段落对照：六项守恒核验（数字/单位/引用/公式/否定/术语） |
| 3 | 文献总结与结构化笔记 | [`paper-notes/`](paper-notes/) | 章节对齐笔记 + 论文卡片（7 字段必带锚点）+ 覆盖度与数字溯源核查 |
| 4 | 纳米出版 | [`nanopublication/`](nanopublication/) | 断言拆解 + 最小证据片段绑定 + 来源元数据 + 过宽/证据/重复/来源 质量检查 |
| 5 | 文献知识图谱构建 | [`knowledge-graph/`](knowledge-graph/) | 五类实体 + 五类关系抽取、别名归一与同名消歧、建图与三个真实查询 |
| 6 | 学术语言润色 | [`academic-polish/`](academic-polish/) | 最小编辑润色：限定强度守恒、数字与引用不动、逐句修改记录 |
| 7 | 参考文献与引文管理 | [`citation-manager/`](citation-manager/) | 引用解析、七项一致性核查、按首次出现重排编号、去重合并、旧→新映射 |
| 8 | 引言与相关工作写作 | [`intro-related-work/`](intro-related-work/) | 4 段式骨架 + 引用覆盖/空转句/分组维度/空白推导/贡献证据 六项校验 |
| 9 | 方法与实验章节写作 | [`methods-experiments/`](methods-experiments/) | 步骤/参数表/数据集解析、config 校正、复现要素与一致性校验 |
| 10 | LaTeX 写作与编译 | [`latex-writer/`](latex-writer/) | 结构化组装 + 转义 + 八项静态检查（带行号）+ 可选实测编译 |

## 共同设计原则

1. **可核验**：每个输出都带锚点（段落/页/块/行号），能点回原文
2. **诚实**：缺失写 `not_reported` / `not_recorded` / `partial` 并列出 `todo`，不编造数据、文献或编译结果
3. **守恒**：改写/翻译/重排时不改变数字、单位、引用编号、图表指向与主张强度
4. **可复用**：规则表（`rules/*.md`）与脚本解耦，换学科只需换术语表与字段字典

## 每个作品的统一结构

```
SKILL.md                 技能入口（YAML frontmatter + 流程 + 契约 + 异常处理）
environment/resources.yaml  资源清单
rules/*.md               判定口径（可独立阅读、可被替换）
scripts/*.py             可执行脚本（Python 3.8+ 标准库，无第三方依赖）
templates/               输出结构 / 输入模板
examples/                最小示例与示意输出（非正式答案）
```

## 本地运行

```bash
python3 scripts/<script>.py --help
```

依赖：Python 3.8+ 标准库。`pdf-parser` 可选依赖 `pdftotext`；`latex-writer` 可选依赖 `latexmk/pdflatex/xelatex`（缺失时只做静态检查并如实标注）。

## 许可

仅用于赛事提交与学术交流。
