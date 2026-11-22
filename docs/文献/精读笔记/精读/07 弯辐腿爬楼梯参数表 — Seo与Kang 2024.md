<!-- 镜像自 Obsidian 库 越障仿真/，**以库内文件为准**；修改请先改库，再跑 scripts/sync-lit-notes.sh -->
---
类型: 文献精读
状态: 未读
zotero_key: XWNNVUYS
doi: 10.3390/biomimetics9100633
优先级: 选读
阅读序: 7
pdf: refs/Seo_Kang_2024_Biomimetics_stair_climbing.pdf
tags: [越障, 台阶, 轮腿]
---

# 轮径小于台阶高度时，必须靠附加机构——弯辐腿给出的参数边界

**论文**：Seo, Kang, *Stair-Climbing Wheeled Robot Based on Rotating Locomotion of Curved-Spoke Legs*, Biomimetics 9(10): 633, 2024。[DOI](https://doi.org/10.3390/biomimetics9100633)；[Zotero](zotero://select/library/items/XWNNVUYS)。

**已阅读范围**：仅按清单定位到 Table 1、Fig. 5、Fig. 8、Fig. 13，未通读。

## 核心结论与研究设计

清单把这篇当作“轮径小于台阶高度”的完整参数对照：m=30 kg、R=80 mm、台阶 H=150 mm、W=250 mm、L=580 mm、μ=0.3。

- 参数：Table 1 给系统参数（质量、轮径、台阶宽高、轮距、轴距、摩擦系数）。
- 运动：Fig. 5 给单轮三阶段；Fig. 8 给所需摩擦系数；Fig. 13 给弯辐腿关节扭矩曲线。

## 核心证据与异常

| 问题 | 论文证据（页码 / 公式号 / 表号） | 解释与边界 |
| --- | --- | --- |
| h>R 时靠什么过台阶？ | Table 1（H=150 mm > R=80 mm）+ Fig. 5 单轮三阶段 | 靠弯辐腿的附加机构，不是靠轮径；不能把结论直接搬到普通轮组。 |
| 摩擦系数需求怎么变？ | Fig. 8：所需摩擦系数 | 曲线对应 μ=0.3 的参数集，换 μ 要重算。 |
| 关节扭矩多大？ | Fig. 13：关节扭矩曲线 | 是弯辐腿关节，不是驱动轮扭矩，不能与轮组峰值扭矩直接比。 |

**不能外推的地方**：弯辐腿不是扫地机轮组；30 kg / 80 mm 也不是本机，只作极端对照。

## 项目应用

- 验证“h>R 时必须靠附加机构”的边界条件。
- 给首版参数扫描一个极端对照：R=80 mm、H=150 mm。

## 待读

- [ ] Table 1：系统参数（m=30 kg、R=80 mm、H=150 mm、W=250 mm、L=580 mm、μ=0.3）
- [ ] Fig. 5：单轮三阶段
- [ ] Fig. 8：所需摩擦系数
- [ ] Fig. 13：关节扭矩
