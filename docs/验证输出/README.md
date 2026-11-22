# 验证输出索引

本目录只放**可共享的文本证据**（`.txt` / `.json` / `.csv`），不放 `outputs/` 下的完整时程、二进制或受限数据。完整批次目录按 `docs/仿真环境安装与版本.md` 的命令在 Windows 生成，不入库。

## 1. 文件清单

| 文件 | 来源 | 说明 |
| --- | --- | --- |
| `2026-11-21_接触力读数_3f8b993.txt` | main / #2 | 接触力读数校验原始输出（`mj_contactForce`） |
| `2026-11-21_环境基线_pip_check_d121b86.txt` | main / #2 | `pip check` 环境基线 |
| `2026-11-21_环境基线_verify_env_d121b86.txt` | main / #2 | `verify_env.py` 冒烟输出 |
| `2026-11-22_接触力读数_pyramidal_ddf0d57a.txt` | PR #13 | 金字塔锥接触力读数；法向误差 0.000000% |
| `2026-11-22_接触力读数_elliptic_ddf0d57a.txt` | PR #13 | 椭圆锥接触力读数；锥间差 0.000000% |
| `2026-11-22_原型批次_pyramidal_run.json` | PR #13 | 原型主批次（pyramidal，2 ms）的批次元数据、参数标签与判定 |
| `2026-11-22_原型批次_pyramidal_summary.csv` | PR #13 | 同批次的逐算例摘要 |
| `2026-11-22_原型批次_elliptic_run.json` | PR #13 | 锥型对照批次（elliptic） |
| `2026-11-22_原型批次_elliptic_summary.csv` | PR #13 | 同批次的逐算例摘要 |
| `2026-11-22_原型批次_repeat2_run.json` | PR #13 | 重复性批次（repeat 2） |
| `2026-11-22_原型批次_repeat2_summary.csv` | PR #13 | 同批次的逐算例摘要 |

## 2. 来源边界

- PR #13 的 `models/baseline.xml`、`scripts/build_model.py`、`scripts/run_cases.py` **未并入 main**；这些 `2026-11-22_*` 文件是历史证据，不能按当前 main 的 #15 入口复跑。
- 批次记录的解释与限制见[仿真环境安装与版本记录](../仿真环境安装与版本.md)附录。
- 所有力读数只用 `mj_contactForce`；`efc_force` 不进入本目录任何输出列。
- 本目录没有大型二进制、没有受限 CAD/实测数据，因此全部入库；若后续出现时程 CSV 或 `outputs/` 原始目录，按项目 `.gitignore` 与 AGENTS.md 处理，只留本索引和路径说明。

## 3. 原型批次冻结快照（ADR README 第 4 条）

`2026-11-22_原型批次_{pyramidal,elliptic,repeat2}_run.json` 与对应 `_summary.csv`：

```text
frozen_at=2026-11-22
ref=PR #13 @ f428c197dc2ca48062eb01ad331216824d552ab0
```

这批文件是**冻结快照**，只用于重建当时那批判定，**不参与现行裁决**，也不随契约版本追新。三个 run.json 顶层已写入 `frozen_at` / `ref` / `frozen_note`；`summary.csv` 由同批 run.json 约束。现行结论请用当前 `run_cases` 生成的 `2026-11-22_G2-返工二轮/` 与 `2026-11-22_G2-浮点容差/`。
