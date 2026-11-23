# 文献原件（PDF）

2026-11-23 老板要求把文献推到 git 上，因此本目录从 `.gitignore` 里放出来入库。
**入库不等于可公开**：项目转 public 前必须按下表口径筛选。

2026-11-23 公开前清理：原分支共 11 篇 PDF（46.9 MB），已将 **5 篇不能/待核公开的文献从 git 历史中移出**（旧提交不可达，由 GitHub GC 回收）。现在仓库内只保留 **6 篇**（18.6 MB），其中 Wilhelm 学位论文仍在「待核」状态。
**非公开文献不入库**（不随仓库分发）：`refs/*.pdf` 默认被 `.gitignore` 忽略，仅下表 6 篇为白名单例外；本机留存请放 `refs/_private/`（已被忽略）。

索引与精读笔记在 `docs/文献/精读笔记/文献索引.md`（13 条），两处对应关系见下表编号。

## 入库清单（6 篇，可随公开仓库分发）

| # | 文件 | 大小 | sha256 前 16 位 | 出处 | 许可 |
| --- | --- | --- | --- | --- | --- |
| 03 | `Dyson_GB2611795A.pdf` | 1.5M | `134e0b4de6476f01` | GB2611795A（Google Patents） | 专利公开文本 ✅ |
| 04 | `Dreame_CN117958664B.pdf` | 592K | `520bd0ae58d0ff2d` | CN117958664B（Google Patents） | 专利公开文本 ✅ |
| 07 | `Seo_Kang_2024_Biomimetics_curved_spoke_stair.pdf` | 1.2M | `babf7de10146c0b9` | Biomimetics 9(10):633，DOI 10.3390/biomimetics9100633 | CC-BY 4.0（MDPI） ✅ |
| 08 | `Fan_2025_Machines_wheeled_climbing.pdf` | 4.6M | `93bb9a45ca6abb33` | Machines 13(8):674，DOI 10.3390/machines13080674 | CC-BY 4.0（MDPI） ✅ |
| 09 | `Won_2022_SciRep_2DOF_wheel.pdf` | 2.6M | `718b3ad8e802aac5` | Scientific Reports 12，DOI 10.1038/s41598-022-21410-1 | CC-BY 4.0 ✅ |
| — | `Wilhelm_2007_thesis.pdf` | 8.1M | `60d3d9fce60ba85f` | 学位论文（非索引 13 条之一，作为 01 的补充材料） | ⚠️ **待核：暂不公开引用**（学位论文授权不明） |

合计 6 个 PDF，约 18.6 MB；单个最大 8.1 MB，未超 GitHub 单文件 100 MB 限制，不需要 Git LFS。

## 已移除：不便公开（不随仓库分发）

以下 5 篇已从 `docs/lit` 历史中移出，仅保留可查标识；需要原文请通过 DOI / arXiv 自行获取，仓库不提供下载。

| # | 文献 | 可查标识 | 移除原因 |
| --- | --- | --- | --- |
| 01 | Wilhelm 2007, IROS, deformable wheel step | DOI 10.1109/IROS.2007.4399601 | 已移除：不便公开（不随仓库分发），出版社版权（IEEE） |
| 05 | Choi 等 2017, Mechanism and Machine Theory, required friction | DOI 10.1016/j.mechmachtheory.2017.03.018 | 已移除：不便公开（不随仓库分发），出版社版权（Elsevier） |
| 10 | Chamorro 等 2024, 轮腿盲爬台阶 | arXiv:2402.06143 | 已移除：不便公开（不随仓库分发），arXiv 条目页未确认 CC 许可 |
| 11 | Gasparino 等 2022, 轮地牵引在线估计 | arXiv:2203.12071；RA-L DOI 10.1109/LRA.2022.3193464 | 已移除：不便公开（不随仓库分发），arXiv 条目页未确认 CC 许可 |
| 12 | Kovalev 等 2025, MuJoCo-XLA 系统辨识 | arXiv:2508.04696 | 已移除：不便公开（不随仓库分发），arXiv 条目页未确认 CC 许可 |

另：`02` IEC 62849:2025 为付费标准、`06` Cui 2016 尚未取到原件、`13` MuJoCo 官方文档不存 PDF，均不入库。

## 复核方法

```bash
shasum -a 256 refs/*.pdf      # 与上表前 16 位对齐即可确认文件未被替换
```
