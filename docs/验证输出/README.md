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
