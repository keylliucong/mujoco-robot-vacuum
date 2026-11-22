<!-- 镜像自 Obsidian 库 越障仿真/，**以库内文件为准**；修改请先改库，再跑 scripts/sync-lit-notes.sh -->
---
类型: 文献精读
状态: 未读
zotero_key: AEQM86P8
doi: 
优先级: 选读
阅读序: 13
pdf: 
tags: [仿真, MuJoCo, 参数语义]
---

# solimp 是 5 参数、cone 默认 pyramidal、integrator 默认 Euler——写 MJCF 前按版本核对

**论文**：MuJoCo Documentation（Google DeepMind），[Computation](https://mujoco.readthedocs.io/en/stable/computation/index.html)、[Modeling / Solver parameters](https://mujoco.readthedocs.io/en/stable/modeling.html)、[XML Reference](https://mujoco.readthedocs.io/en/stable/XMLreference.html)。[Zotero](zotero://select/library/items/AEQM86P8)。无 DOI。

**已阅读范围**：网页文档，按清单定位到 Solver parameters 的 `solref`/`solimp` 段与 XML Reference 的 `option cone/integrator`、`actuator forcerange`、`joint actuatorfrcrange`；未逐条抄录。

## 核心结论与研究设计

清单把官方文档定为参数语义的最终依据：本轮已确认 `solimp` 是 5 参数 `(d0,dw,width,midpoint,power)`、`cone` 默认 pyramidal、`integrator` 默认 Euler；写 MJCF 前必须按实际版本核对。

- Solver parameters：`solref` / `solimp` 段。[modeling.html]
- XML Reference：`option cone/integrator`、`actuator forcerange`、`joint actuatorfrcrange`。[XMLreference.html]
- 版本：本项目在 MuJoCo 4.0.1 上验证，文档默认值可能随版本变化。

## 核心证据与异常

| 问题 | 论文证据（页码 / 公式号 / 表号） | 解释与边界 |
| --- | --- | --- |
| `solimp` 有几个参数？ | Solver parameters：`(d0, dw, width, midpoint, power)` 5 参数 | 不同版本可能改默认值，引用时写版本号。 |
| 摩擦锥默认是什么？ | `option cone` 默认 pyramidal | pyramidal 与 elliptic 的接触行为不同，报告里必须写明实际设置。 |
| 积分器默认是什么？ | `option integrator` 默认 Euler | 换 integrator 会改接触刚度表现，不能混用结果。 |

**不能外推的地方**：默认值随版本变化；必须按项目实际使用的 4.0.1 核对，不能凭本笔记转述当版本依据。

## 项目应用

- 写 MJCF 时按 XML Reference 核对 `solref`/`solimp`、`cone`、`integrator`、`forcerange`/`actuatorfrcrange`。
- 报告里记录实际版本与求解器配置（时间步、integrator、cone、solimp）。

## 待读

- [ ] Solver parameters 的 `solref` / `solimp` 段
- [ ] XML Reference：`option cone` / `option integrator`
- [ ] XML Reference：`actuator forcerange`、`joint actuatorfrcrange`
- [ ] 核对本地 4.0.1 的默认值是否与 stable 文档一致
