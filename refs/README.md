# 文献原件（PDF）

> **本目录收录仅供本项目内部研究使用；如权利人提出异议，将立即移除。**

2026-11-23 老板要求把文献推到 git 上，因此本目录从 `.gitignore` 里放出来入库。
2026-11-23 晚老板再次确认：**剩余 5 篇也要上传原文**，仓库已转 public，已知版权风险并选择公开；本目录因此收录 11 篇，其中 5 篇为出版社版权或版本待核（见下文标注），并非全部可自由再分发。

`refs/*.pdf` 默认被 `.gitignore` 忽略，仅下表 11 篇按文件名逐个白名单放行（不使用目录通配）。本机留存的其他原件请放 `refs/_private/`（已被忽略）。

索引与精读笔记在 `docs/文献/精读笔记/文献索引.md`（13 条），两处对应关系见下表编号。

## 入库清单（11 篇）

| # | 文件 | 大小 | sha256 前 16 位 | 出处 | 许可 / 状态 |
| --- | --- | --- | --- | --- | --- |
| 01 | `Wilhelm_2007_IROS_deformable_wheel_step.pdf` | 376K | `fac2e3e4dcef059e` | IEEE IROS 2007，DOI 10.1109/IROS.2007.4399601 | ⚠️ **出版社版权（IEEE），未获再分发许可** |
| 03 | `Dyson_GB2611795A.pdf` | 1.5M | `134e0b4de6476f01` | GB2611795A（Google Patents） | 专利公开文本 ✅ |
| 04 | `Dreame_CN117958664B.pdf` | 592K | `520bd0ae58d0ff2d` | CN117958664B（Google Patents） | 专利公开文本 ✅ |
| 05 | `Choi_2017_MMT_required_friction.pdf` | 3.7M | `8392ff605f854809` | Mechanism and Machine Theory，DOI 10.1016/j.mechmachtheory.2017.03.018 | ⚠️ **出版社版权（Elsevier），未获再分发许可** |
| 07 | `Seo_Kang_2024_Biomimetics_curved_spoke_stair.pdf` | 1.2M | `babf7de10146c0b9` | Biomimetics 9(10):633，DOI 10.3390/biomimetics9100633 | CC-BY 4.0（MDPI） ✅ |
| 08 | `Fan_2025_Machines_wheeled_climbing.pdf` | 4.6M | `93bb9a45ca6abb33` | Machines 13(8):674，DOI 10.3390/machines13080674 | CC-BY 4.0（MDPI） ✅ |
| 09 | `Won_2022_SciRep_2DOF_wheel.pdf` | 2.6M | `718b3ad8e802aac5` | Scientific Reports 12，DOI 10.1038/s41598-022-21410-1 | CC-BY 4.0 ✅ |
| 10 | `Chamorro_2024_arXiv_2402.06143.pdf` | 15M | `72f0ba9f08226542` | arXiv:2402.06143 | ⚠️ arXiv 预印本，**版本待核**（未确认 CC 许可） |
| 11 | `Gasparino_2022_arXiv_2203.12071.pdf` | 5.2M | `99d995749fbf409d` | arXiv:2203.12071；RA-L DOI 10.1109/LRA.2022.3193464 | ⚠️ arXiv 预印本，**版本待核**（未确认 CC 许可） |
| 12 | `Kovalev_2025_arXiv_2508.04696.pdf` | 4.3M | `9b82dcaf6d66f2e4` | arXiv:2508.04696 | ⚠️ arXiv 预印本，**版本待核**（未确认 CC 许可） |
| — | `Wilhelm_2007_thesis.pdf` | 8.1M | `60d3d9fce60ba85f` | 学位论文（非索引 13 条之一，作为 01 的补充材料） | ⚠️ **待核：学位论文授权不明** |

合计 11 个 PDF，约 47 MB；单个最大 15 MB，未超 GitHub 单文件 100 MB 限制，不需要 Git LFS。

## 版权与许可状态说明（5 篇新增）

**出版社版权，未获再分发许可**（仅因项目内部研究需要而随私有→公开仓库保留）：

- `Choi_2017_MMT_required_friction.pdf` — Elsevier / *Mechanism and Machine Theory*，**出版社版权，未获再分发许可**；正式引用请用 DOI 10.1016/j.mechmachtheory.2017.03.018。
- `Wilhelm_2007_IROS_deformable_wheel_step.pdf` — IEEE IROS 2007，**出版社版权，未获再分发许可**；正式引用请用 DOI 10.1109/IROS.2007.4399601。

**arXiv 预印本，版本待核**（仓库内为下载时的 arXiv PDF，可能早于或不同于正式出版版本，引用前请核对版本；以下 arXiv 链接是推荐的合法引用方式）：

- `Chamorro_2024_arXiv_2402.06143.pdf` — arXiv:2402.06143，https://arxiv.org/abs/2402.06143
- `Gasparino_2022_arXiv_2203.12071.pdf` — arXiv:2203.12071，https://arxiv.org/abs/2203.12071 （正式版：RA-L，DOI 10.1109/LRA.2022.3193464）
- `Kovalev_2025_arXiv_2508.04696.pdf` — arXiv:2508.04696，https://arxiv.org/abs/2508.04696

另：`02` IEC 62849:2025 为付费标准、`06` Cui 2016 尚未取到原件、`13` MuJoCo 官方文档不存 PDF，均不入库。

## 复核方法

```bash
shasum -a 256 refs/*.pdf      # 与上表前 16 位对齐即可确认文件未被替换
```
