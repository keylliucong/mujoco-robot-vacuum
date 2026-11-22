<!-- 镜像自 Obsidian 库 越障仿真/，**以库内文件为准**；修改请先改库，再跑 scripts/sync-lit-notes.sh -->
---
类型: 文献精读
状态: 未读
zotero_key: MPHZIJ6J
doi: 
优先级: 选读
阅读序: 12
pdf: refs/Kovalev_2025_arXiv_2508.04696.pdf
tags: [系统辨识, MuJoCo, 参数标定]
---

# 只靠轨迹和控制输入，就能辨识 armature / frictionloss / damping

**论文**：Kovalev, Chaikovskaia, Davydenko, Gorbachev, *Achieving Precise and Reliable Locomotion with Differentiable Simulation-Based System Identification*, arXiv:2508.04696, 2025。[arXiv](https://arxiv.org/abs/2508.04696)；[Zotero](zotero://select/library/items/MPHZIJ6J)。无 DOI（预印本）。

**已阅读范围**：仅按清单定位到 Sec. IV、Figs 3/4，未通读。

## 核心结论与研究设计

清单把这篇当作 R6 辨识流程的方法来源：只用轨迹（位置/速度）和控制输入，在 MuJoCo-XLA 中优化 `armature`、`frictionloss`、`damping`。

- 设置：1 ms 重采样、显式 Euler、分段 N=4。[Sec. IV]
- 结果：损失降约 20%，测试 MSE 约降至 1/8。[Sec. IV]
- 收敛：Figs 3/4 给参数收敛与误差。

## 核心证据与异常

| 问题 | 论文证据（页码 / 公式号 / 表号） | 解释与边界 |
| --- | --- | --- |
| 辨识需要什么数据？ | Sec. IV：只要轨迹（位置/速度）+ 控制输入 | 不需要力矩传感器，但需要足够激励；静止段学不到阻尼。 |
| 优化哪些参数？ | `armature`、`frictionloss`、`damping` | 这三个是传动/关节参数，不含轮胎或地面接触参数。 |
| 效果多大？ | 损失降约 20%，测试 MSE 约降至 1/8 [Sec. IV] | 是该作者平台的结果，不能当本机保证值。 |

**不能外推的地方**：没有辨识轮胎/地面接触参数；接触参数仍要单独标定，不能用这篇的流程代替。

## 项目应用

- 按 R6 的“单电机台架 → 单轮 → 整机”顺序搭辨识流程。
- 用 1 ms 重采样、显式 Euler、分段 N=4 作为起点配置，并记录到报告。
- 把 `armature` / `frictionloss` / `damping` 与接触参数分开标定。

## 待读

- [ ] Sec. IV：方法（重采样、积分器、分段 N=4）
- [ ] Figs 3/4：参数收敛与误差
- [ ] 损失降幅与测试 MSE 的原始数字
