# G2 验收证据（报告摘录）

**这三份是 G2 的验收证据，不是结论**：G2 的实现基线只认已合入 `main` 的 #15（`f712289`），本目录只留存 #17 / #27 / #28 三支已关闭分支的过程报告，供验收时追溯失败模式、契约缺口和数据来源，不作通过/不通过判定。

| 文件 | 来源分支 / PR | 摘录提交 | 摘录日期 | 报告内的实跑或抽查基线 |
|---|---|---|---|---|
| [全流程试跑-oomwoo.md](全流程试跑-oomwoo.md) | `dryrun/oomwoo-step` / [#17](https://github.com/keylliucong/mujoco-robot-vacuum/pull/17) | `76e57a0785060e7f7754a44e9d44079a1ca6312b` | 2026-11-22 | Windows 实跑 `325e543f4afea19a30928f2cab7fe5dec6a47a9c` |
| [干跑-契约暴露的问题.md](干跑-契约暴露的问题.md) | `dryrun/oomwoo` / [#27](https://github.com/keylliucong/mujoco-robot-vacuum/pull/27) | `ea544fafa47cb561409155051a5d3305887303ff` | 2026-11-22 | S24 返工 `d91741192e6c350137394938aa72f537a817068a` |
| [结构抽查-16项.md](结构抽查-16项.md) | `qa/g2-check` / [#28](https://github.com/keylliucong/mujoco-robot-vacuum/pull/28) | `bffb193204202068edc47a08b1fd7defef6a3c40` | 2026-11-22 | 抽查对象 `feature/g2-baseline-runner` @ `c52b229cfc45eccbefe989fe1d9d81346335bc4b` |

## 口径

- 三份文件只在文首加一行来源说明，正文报告原文未改。
- `models/`、`cases/`、`scripts/`、`judge.py` 等实现一律不取自这三支分支，以 #15 合入 `main` 的版本为准。
- #21（viewer）不在本轮摘录与关闭范围内。
- 本目录取代先前的同内容摘录（`docs/干跑/`、`docs/试跑/`、`docs/评审/G2-结构抽查-2026-11-22.md`），避免同一报告出现新旧两版。
