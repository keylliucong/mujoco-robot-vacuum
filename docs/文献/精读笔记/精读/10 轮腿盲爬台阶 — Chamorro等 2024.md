<!-- 镜像自 Obsidian 库 越障仿真/，**以库内文件为准**；修改请先改库，再跑 scripts/sync-lit-notes.sh -->
---
类型: 文献精读
状态: 未读
zotero_key: QVMDWS43
doi: 
优先级: 选读
阅读序: 10
pdf: refs/Chamorro_2024_arXiv_2402.06143.pdf
tags: [越障, sim-to-real, 摩擦随机化]
---

# 摩擦随机化过高，会让仿真学到“夹住台阶”的非物理策略

**论文**：Chamorro, Klemm, de la Iglesia Valls, Pal, Siegwart, *Reinforcement Learning for Blind Stair Climbing with Legged and Wheeled-Legged Robots*, arXiv:2402.06143, 2024。[arXiv](https://arxiv.org/abs/2402.06143)；[Zotero](zotero://select/library/items/QVMDWS43)。无 DOI（预印本）。

**已阅读范围**：仅按清单定位到 Sec. III-C、Table III、Fig. 6，未通读。

## 核心结论与研究设计

清单把这篇当作仿真到实机迁移的反例来源：Ascento 实机爬 15 cm 台阶，Table III 给 14–30 cm 的仿真成功率。

- 实机：15 cm 台阶。[Fig. 6]
- 仿真：14–30 cm 成功率。[Table III]
- 陷阱：摩擦随机化过高，机器人会学到“夹住台阶”的非物理策略，迁移失败。[Sec. III-C]
- 延迟：训练中模拟 20 ms 控制延迟。[Sec. III-C]

## 核心证据与异常

| 问题 | 论文证据（页码 / 公式号 / 表号） | 解释与边界 |
| --- | --- | --- |
| 摩擦随机化越大越稳吗？ | Sec. III-C：随机化过高 → 学到“夹住台阶”的非物理策略 → 迁移失败 | 这是本任务里最重要的反例：首版参数不要为了“能过”把摩擦调高。 |
| 仿真成功率说明什么？ | Table III：14–30 cm 的仿真成功率 | 成功率是仿真内的，不等于实机；报告不能拿它当通过证据。 |
| 控制延迟要不要建模？ | Sec. III-C：训练中模拟 20 ms 控制延迟 | 本机控制链路延迟需实测后再定值，不能直接套 20 ms。 |

**不能外推的地方**：轮腿机器人，不是被动轮组；结论用于“方法警示”，不能当本机越障判据。

## 项目应用

- 接触摩擦参数按实测/文献给范围，禁止为“能过”上调。
- 报告里记录控制延迟；仿真里显式加延迟项。
- 解释“仿真通过但实机失败”时，先查是否学到非物理策略。

## 待读

- [ ] Sec. III-C：sim-to-real（摩擦随机化、20 ms 延迟）
- [ ] Table III：14–30 cm 仿真成功率
- [ ] Fig. 6：实机 15 cm 台阶
