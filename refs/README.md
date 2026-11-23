# 文献原件（PDF）

2026-11-23 老板要求把文献推到 git 上，因此本目录从 `.gitignore` 里放出来入库。

2026-11-23 公开前清理时曾将 5 篇从 git 历史中移出（旧提交不可达，由 GitHub GC 回收）。

2026-11-23 恢复：老板确认「都加回仓库，版权风险由所有者承担」，5 篇已**按所有者授权重新收录**，现为 **11 篇全部入库**（约 46.9 MB）。

> 版权说明：本仓库对以下文献的收录经仓库所有者授权，仅用于个人研究与内部复现；出版社版权文献（Elsevier / IEEE）的再分发权未取得，如需对外引用请以出版社原文为准。若权利人提出异议，将立即移除。

`refs/*.pdf` 默认被 `.gitignore` 忽略，仅下表 11 篇为白名单例外；未列入的 PDF 与私有原件不入库，本机留存请放 `refs/_private/`（已被忽略）。

索引与精读笔记在 `docs/文献/精读笔记/文献索引.md`（13 条），两处对应关系见下表编号。

## 入库清单（11 篇，全部按所有者授权入库）

| # | 文件 | 大小 | sha256 前 16 位 | 出处 | 许可 / 版权 |
| --- | --- | --- | --- | --- | --- |
| 01 | `Wilhelm_2007_IROS_deformable_wheel_step.pdf` | 372K | `fac2e3e4dcef059e` | IROS 2007，DOI 10.1109/IROS.2007.4399601 | ⚠️ 出版社版权（IEEE）；按所有者授权收录，再分发权未取得 |
| 03 | `Dyson_GB2611795A.pdf` | 1.5M | `134e0b4de6476f01` | GB2611795A（Google Patents） | 专利公开文本 |
| 04 | `Dreame_CN117958664B.pdf` | 592K | `520bd0ae58d0ff2d` | CN117958664B（Google Patents） | 专利公开文本 |
| 05 | `Choi_2017_MMT_required_friction.pdf` | 3.7M | `8392ff605f854809` | Mechanism and Machine Theory，DOI 10.1016/j.mechmachtheory.2017.03.018 | ⚠️ 出版社版权（Elsevier）；按所有者授权收录，再分发权未取得 |
| 07 | `Seo_Kang_2024_Biomimetics_curved_spoke_stair.pdf` | 1.2M | `babf7de10146c0b9` | Biomimetics 9(10):633，DOI 10.3390/biomimetics9100633 | CC-BY 4.0（MDPI） |
| 08 | `Fan_2025_Machines_wheeled_climbing.pdf` | 4.6M | `93bb9a45ca6abb33` | Machines 13(8):674，DOI 10.3390/machines13080674 | CC-BY 4.0（MDPI） |
| 09 | `Won_2022_SciRep_2DOF_wheel.pdf` | 2.6M | `718b3ad8e802aac5` | Scientific Reports 12，DOI 10.1038/s41598-022-21410-1 | CC-BY 4.0 |
| 10 | `Chamorro_2024_arXiv_2402.06143.pdf` | 14.9M | `72f0ba9f08226542` | arXiv:2402.06143（轮腿盲爬台阶），arXiv 版本 | ⚠️ arXiv 预印本，条目页未确认 CC 许可；按所有者授权收录 |
| 11 | `Gasparino_2022_arXiv_2203.12071.pdf` | 5.1M | `99d995749fbf409d` | arXiv:2203.12071，arXiv 版本（RA-L 出版版 DOI 10.1109/LRA.2022.3193464） | ⚠️ arXiv 预印本，条目页未确认 CC 许可；按所有者授权收录 |
| 12 | `Kovalev_2025_arXiv_2508.04696.pdf` | 4.3M | `9b82dcaf6d66f2e4` | arXiv:2508.04696（MuJoCo-XLA 系统辨识），arXiv 版本 | ⚠️ arXiv 预印本，条目页未确认 CC 许可；按所有者授权收录 |
| — | `Wilhelm_2007_thesis.pdf` | 8.1M | `60d3d9fce60ba85f` | 学位论文（非索引 13 条之一，作为 01 的补充材料） | ⚠️ 学位论文授权不明；按所有者授权收录 |

合计 11 个 PDF，约 46.9 MB；单个最大 14.9 MB，未超 GitHub 单文件 100 MB 限制，不需要 Git LFS。

## 不入库文献

`02` IEC 62849:2025 为付费标准、`06` Cui 2016 尚未取到原件、`13` MuJoCo 官方文档不存 PDF，均不入库。

## 复核方法

```bash
shasum -a 256 refs/*.pdf      # 与上表前 16 位对齐即可确认文件未被替换
```
