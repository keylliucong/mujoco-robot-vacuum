# PDF 获取情况（越障动力学文献）

- 整理日期：2026-11-22
- 来源清单：`docs/文献阅读清单.md`（分支 `origin/资料检索`）
- PDF 存放位置：`/Users/liucong/orca/projects/mujoco_/refs/`（本机路径，不进 Git；清单正文里写的仓库根目录 `refs/` 未使用）
- 本文件只记录**取到了什么、没取到什么**，不做文献分析、不下结论。

## 汇总

| 项 | 数值 |
| --- | --- |
| 任务表内条目 | 12 |
| 任务表内拿到 PDF | 9（ Wilhelm IROS、Wilhelm 学位论文、Dyson、Dreame、Seo & Kang、Fan、Won、Chamorro、Gasparino ） |
| 任务表内未拿到 | 3（IEC 62849:2025、Choi 2017、Cui 2016） |
| 清单内额外拿到 | 1（Kovalev 2025 arXiv） |
| `refs/` 实际 PDF 数 | 10 |
| `refs/` 合计大小 | 约 48 MB |

下载渠道只用开放获取出版商 / 作者机构主页 / arXiv / Google Patents 官方 PDF；未使用 sci-hub 一类镜像。

## 逐条情况

| 条目 | 本地 PDF（`refs/`） | 来源链接 | 获取方式 | 文件大小 / 页数 |
| --- | --- | --- | --- | --- |
| Wilhelm et al. 2007, IROS《Dynamics of step-climbing with deformable wheels》 | `Wilhelm_2007_IROS_deformable_wheel_step.pdf` | DOI [10.1109/IROS.2007.4399601](https://doi.org/10.1109/IROS.2007.4399601)；实际下载 [作者机构页 HMC LAIR](https://www.hmc.edu/lair/publications/2007/wilhelm_iros_2007.pdf) | 机构主页 OA（IEEE 正式版付费，作者本人机构公开副本） | 380,992 B / 6 页 |
| Wilhelm 2007 学位论文《Design of a Mobile Robotic Platform with Variable Footprint》 | `Wilhelm_2007_thesis.pdf` | [作者机构页 HMC LAIR](https://www.hmc.edu/lair/publications/2007/wilhelm_thesis_2007.pdf)；馆藏记录 [UWSpace hdl 10012/3338](https://uwspace.uwaterloo.ca/items/d476090b-e49b-4502-8608-f1e8926250ba) | 机构主页 OA（Waterloo 仓储有反爬，改用 HMC 副本） | 8,443,524 B / 275 页 |
| IEC 62849:2025 §6.1.2–6.1.3 | 无 | [IEC Webstore](https://webstore.iec.ch/en/publication/68511) | **拿不到：标准未购买**，仅按任务要求记状态，未尝试绕过付费 | — |
| Dyson GB2611795A | `Dyson_GB2611795A.pdf` | [Google Patents GB2611795A](https://patents.google.com/patent/GB2611795A/en) → `patentimages.storage.googleapis.com/.../GB2611795A.pdf` | 专利（Google Patents 页面内 `citation_pdf_url`） | 1,585,260 B / 34 页（扉页为扫描图像，无可提取文字） |
| Dreame CN117958664B | `Dreame_CN117958664B.pdf` | [Google Patents CN117958664B](https://patents.google.com/patent/CN117958664B/zh) → `patentimages.storage.googleapis.com/.../CN117958664B.pdf` | 专利（同上） | 604,198 B / 17 页 |
| Choi et al. 2017, RHyMo《…required coefficient of friction…》 | 无 | DOI [10.1016/j.mechmachtheory.2017.03.018](https://doi.org/10.1016/j.mechmachtheory.2017.03.018) | **拿不到：Elsevier 付费**；Unpaywall 报 `is_oa: false`，OpenAlex 无 OA 副本，未找到可读原文 | — |
| Cui et al. 2016, wheel/track mobile robot | 无 | DOI [10.1177/1687814016679763](https://doi.org/10.1177/1687814016679763)；[DOAJ 记录](https://doaj.org/article/a699b3e0565042cab41915d2fec350ac) | **拿不到**：文章本身是 OA（CC BY），但 SAGE 的 `doi/pdf/...` 端点对多种请求头均返回 403（反爬拦截），未绕行 | — |
| Seo & Kang 2024, Biomimetics《Stair-Climbing Wheeled Robot Based on Rotating Locomotion of Curved-Spoke Legs》 | `Seo_Kang_2024_Biomimetics_curved_spoke_stair.pdf` | DOI [10.3390/biomimetics9100633](https://doi.org/10.3390/biomimetics9100633)；实际下载 [mdpi-res `biomimetics-09-00633`](https://mdpi-res.com/d_attachment/biomimetics/biomimetics-09-00633/article_deploy/biomimetics-09-00633.pdf) | MDPI OA（`www.mdpi.com/.../pdf` 返回 403，改用 mdpi-res 附件直链） | 1,257,604 B / 19 页 |
| Fan et al. 2025, Machines | `Fan_2025_Machines_wheeled_climbing.pdf` | DOI [10.3390/machines13080674](https://doi.org/10.3390/machines13080674)；实际下载 [mdpi-res `machines-13-00674`](https://mdpi-res.com/d_attachment/machines/machines-13-00674/article_deploy/machines-13-00674.pdf) | MDPI OA（同上） | 4,839,836 B / 19 页 |
| Won et al. 2022, Scientific Reports | `Won_2022_SciRep_2DOF_wheel.pdf` | DOI [10.1038/s41598-022-21410-1](https://doi.org/10.1038/s41598-022-21410-1)；PDF [nature.com](https://www.nature.com/articles/s41598-022-21410-1.pdf) | 出版商 OA（Nature 直链） | 2,770,319 B / 13 页 |
| Chamorro et al. 2024 | `Chamorro_2024_arXiv_2402.06143.pdf` | [arXiv:2402.06143](https://arxiv.org/abs/2402.06143) | arXiv | 15,574,970 B / 7 页 |
| Gasparino et al. 2022, WayFAST（RA-L DOI 10.1109/LRA.2022.3193464） | `Gasparino_2022_arXiv_2203.12071.pdf` | [arXiv:2203.12071](https://arxiv.org/abs/2203.12071) | arXiv（IEEE 正式版需机构权限，拿的是 arXiv 预印本） | 5,399,010 B / 8 页 |
| Kovalev et al. 2025（清单 §3.3 额外条目） | `Kovalev_2025_arXiv_2508.04696.pdf` | [arXiv:2508.04696](https://arxiv.org/abs/2508.04696) | arXiv | 4,483,412 B / 6 页 |
| 徐锦鑫、王保民 2024，物业清洁机器人越障动力学分析与实验 | 无 | [DOI](http://www.jxyj1978.com/article/doi/10.16576/j.ISSN.1007-4414.2024.04.011) | **拿不到**：期刊站点 PDF 端点为 JS 模板占位，实际请求返回 HTML，未拿到文件 | — |
| 郝为亮等 2021，扫地机器人触发式液压辅助越障机构 | 无 | [DOI](https://www.zjujournals.com/gcsjxb/CN/10.3785/j.issn.1006-754X.2021.00.071) | **拿不到**：Academax 页面只返回前端模板，未暴露 PDF 直链 | — |
| 罗继曼等 2025，变径轮设计与攀爬性能 | 无 | [DOI](https://doi.org/10.16578/j.issn.1004.2539.2025.08.002) | **拿不到**：DOI 解析后未得到可下载 PDF | — |
| MuJoCo 官方文档（Computation / Modeling / XML Reference） | 无（在线网页，非 PDF） | [readthedocs](https://mujoco.readthedocs.io/en/stable/) | 在线文档，本任务不收 PDF | — |
| Roborock 厂商标称参数新闻（heise 等） | 无（HTML 新闻，非 PDF） | [heise IFA 2024](https://www.heise.de/en/news/Vacuum-bot-trends-at-the-IFA-Cleaning-flounders-on-a-climbing-tour-9865351.html?view=print) | 网页新闻，本任务不收 PDF | — |

## 校验

- 10 个文件全部以 `%PDF` 开头，经 `pypdf` 解析成功，页数 6–275，大小 372 KiB–14.9 MiB，均满足「页数 ≥ 1、大小 > 20 KB」。
- 逐篇核对首页文字与 DOI / 标题一致；首次抓 Seo & Kang 时误取了 `biomimetics-10-00633`（另一篇文章），已删除并换为 DOI 对应的 `biomimetics-09-00633`，首页确认为 Seo & Kang 的弯辐腿爬楼梯论文。
- 没有坏文件留存；未改动仓库既有文件。

## 缺原文的后果

以下条目本机**没有原文**。答疑与判据只能引用 `docs/文献阅读清单.md` 及其配套证据表里已经摘录的段落，不能声称读过全文；凡涉及具体页码、公式编号、图表数值的复核，必须明确标注「未读原文、仅据清单摘录」。

- **IEC 62849:2025 §6.1.2–6.1.3**：只能引用证据表 §5.1 的条目与出处；测试床、门槛与起始位置的具体数值、Figure 4 的角度、§6.1.3 的完整判定措辞均不可声称已从原文读到，仿真工况只能说"对齐清单所摘条款"；条文细节只存本地私有摘录。
- **Choi 2017**：只能引用清单里"所需摩擦系数定义、150 mm 台阶整机算例、电机电流对照"几句摘要，不能复述运动静力模型的推导、公式或算例数值；"摩擦系数—台阶高度"判据不得写成来自该文全文。
- **Cui 2016**：只能引用清单已摘的"两阶段划分、Eqs (14)(15)、`h=R` 极限"这几处；Eqs (14)(15) 的具体形式与推导未读到，不能据此直接写校核公式，单轮静力校核只能说"方向性参考、公式待原文核实"。
- **徐锦鑫、王保民 2024**：只有摘要可读（32 mm、10°、垂直/爬坡两套力学模型）；动力学模型的具体方程、样机参数与试验曲线一概不可引用。
- **郝为亮等 2021**：只有摘要可读（驱动轮临界点受力、辅助驱动力公式、ADAMS + 样机）；辅助驱动力公式的具体形式与仿真结果不可引用。
- **罗继曼等 2025**：只有摘要与元数据可读（变径比 1.6、复式六轮瓣、稳定锥、连续台阶样机）；机构尺寸、攀爬性能曲线不可引用。
- **MuJoCo 官方文档**：本任务未收 PDF，只能在线查阅并注明查阅日期与版本；不要写成"已通读文档 PDF"，且 `solimp`/`cone`/`integrator` 的默认值须按实际 MuJoCo 版本在线复核。
- **Roborock 厂商标称参数新闻**：只有 HTML 报道可读，3/4/4.5/8.8 cm 属厂商标称值，未经仪器化验证；不得当作实测越障高度或试验曲线引用。
