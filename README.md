# 扫地机器人越障动力学仿真

用 MuJoCo 分析扫地机器人跨越门槛时的整机动力学，关注通过能力、机身姿态、轮胎打滑、轮组行程、驱动扭矩和底盘托底。首轮以硬质单级门槛为对象，覆盖正向和斜向接近，并用平地行驶作对照。目标机型与门槛尺寸待项目资料确认。

## 当前阶段

第一阶段按[资料检索清单](docs/越障动力学资料检索清单.md)执行，已交付：

- [检索日志与证据表](docs/检索日志与证据表.md)：专利、论文 DOI、IEC 62849:2025 标准台架参数、MuJoCo 官方建模方法与实机资料的出处和条件。
- [仿真参数表](docs/仿真参数表.md)：按"本机实测 / 公开参考 / 工程假设 / 缺失 / 待标定"标记的参数清单。
- [基准工况与数据缺口](docs/基准工况与数据缺口.md)：平地、正向门槛、斜向门槛三类工况的判据、输出、证据与缺口，以及标定/验证补测清单。

Windows 项目级环境已用 Python 3.13.1 和 MuJoCo 4.0.1 跑通；接触力读数已用 `mj_contactForce` 校验（平地静置、30° 斜面静置、密度翻倍三档工况 × 金字塔/椭圆两种摩擦锥，法向/切向/竖直分量误差均小于 0.001%），见[接触力读数校验](docs/接触力读数校验.md)。重建步骤见[仿真环境安装与版本记录](docs/仿真环境安装与版本.md)。扫地机整机模型待建。

下一阶段用通用原型跑通三类工况与参数扫描。本机建模和独立验证依赖目标机型及 CAD、质量/质心/惯量、轮系与悬挂参数、轮端扭矩、摩擦和实测试验。

- [越障动力学 PRD](docs/越障动力学PRD.md)定义首版范围、验收标准和 arXiv 等文献来源。
- [越障动力学实施计划](docs/superpowers/plans/2026-11-21-obstacle-dynamics.md)列出研究、建模、参数扫描与实机验证的任务和依赖。

## 工作位置与环境

| 项目 | 约定 |
| --- | --- |
| Windows 执行入口 | 从当前 Mac 执行 `ssh win` |
| Windows 项目目录 | `E:\mujoco-robot-vacuum` |
| Python 与 MuJoCo | 在项目目录下安装并锁定版本。Python 环境使用 `.venv/` |
| 项目专用 Skill | 放在 `.agents/skills/`，与仓库一起维护 |
| GitHub 同步 | 从 Mac 按检查过的工作增量及时提交和推送。Windows 通过仓库专用的只读部署密钥拉取并检出相应提交 |

[GitHub 私有仓库](https://github.com/keylliucong/mujoco-robot-vacuum)

## 协作流程

1. 从 GitHub 获取最新状态，确认任务分支和基线提交。
2. 在 Mac 上编辑文档或代码。通过 SSH 进入 Windows 的 E 盘项目目录进行环境准备、运行和验证。
3. 确认执行的提交以及 Python、MuJoCo 版本，记录运行路径、结果摘要和数据存放位置。
4. 将可共享的变更提交并推送到对应分支，交接分支、SHA 和验证结果。

各 Agent 开工前先读 [AGENTS.md](AGENTS.md)，其中定义了项目级隔离、同步和交接要求。

Windows 运行前，在 PowerShell 中同步主分支。验证任务分支时，将下面的 `main` 换成已推送的待测分支，或在获取后检出交接指定的提交。

```powershell
Set-Location -LiteralPath 'E:\mujoco-robot-vacuum'
git status --short
git fetch origin
git switch main
git merge --ff-only origin/main
git rev-parse HEAD
```

发现已有未提交改动时，先查明归属，再更新工作区。
