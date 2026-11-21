# 扫地机器人越障动力学仿真

用 MuJoCo 分析扫地机器人跨越门槛时的整机动力学，关注通过能力、机身姿态、轮胎打滑、轮组行程、驱动扭矩和底盘托底。首轮以硬质单级门槛为对象，覆盖正向和斜向接近，并用平地行驶作对照。目标机型与门槛尺寸待项目资料确认。

## 当前阶段

第一阶段按[资料检索清单](docs/越障动力学资料检索清单.md)执行，交付检索证据表、仿真参数表、基准工况及数据缺口。目标机型和关键输入确认后，再建立模型并开展实机对照验证。

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
