# Obsidian 与 Zotero 文献库（越障仿真）

- 建立日期：2026-11-22
- 内容来源：`docs/文献阅读清单.md`（分支 `资料检索`，PR #4）。笔记只做"读哪里、为什么读、用到哪里、不能外推什么"的定位，不写研究结论。
- 本文件说明库在哪、怎么组织、以后怎么加一篇、以及本地 API 能不能写。Obsidian 库本身不在本仓库内，不随 Git 提交。

## 1. 位置

| 用途 | 路径 / 标识 |
| --- | --- |
| Obsidian 库（老板现有库） | `~/Documents/Codex/塑胶疲劳知识库` |
| 本专题文件夹 | `~/Documents/Codex/塑胶疲劳知识库/越障仿真/` |
| Zotero 集合 | `越障仿真`（`FI52Q68X`）→ 子集合 `必读`（`EEMZW8JL`）、`选读`（`MB6KEF5P`） |
| 本地 PDF | 仓库 `refs/`（被 `.gitignore` 忽略）；已上传为 Zotero 条目的 stored attachment |

在 Obsidian 里直接打开现有库即可看到 `越障仿真/`，不需要新建库、不需要重启、不需要切换库。

## 2. 结构

```
越障仿真/
  项目主页.md                  # 用途、阅读顺序勾选、入口链接
  文献索引.md                  # 全部条目 + DOI/链接、状态统计、缺 PDF/缺 DOI 分组
  文献精读/
    01 软胎越台阶峰值扭矩 — Wilhelm 2007.md
    02 标准门槛试验 — IEC 62849 2025.md
    03 双平行臂悬架 — Dyson GB2611795A.md
    04 主动越障的材质阈值 — Dreame CN117958664B.md
    05 所需摩擦系数判据 — Choi等 2017.md
    06 两阶段越台阶方程 — Cui等 2016.md
    07 弯辐腿爬楼梯参数表 — Seo与Kang 2024.md
    08 分阶段越障动力学 — Fan等 2025.md
    09 连杆轮优化 — Won等 2022.md
    10 轮腿盲爬台阶 — Chamorro等 2024.md
    11 轮地牵引在线估计 — Gasparino等 2022.md
    12 MuJoCo-XLA 系统辨识 — Kovalev等 2025.md
    13 MuJoCo 参数语义 — 官方文档.md
  模板/
    文献精读模板.md
```

现状：13 篇笔记（必读 4、选读 9），状态全部为 `未读`；Zotero 侧 14 个条目（13 篇笔记对应的 13 条 + Wilhelm 学位论文 1 条），10 个 PDF 已作为 stored attachment 挂到对应条目。

## 3. 命名与格式规则

- 文件名：`<两位阅读序> <短标题> — <作者 年份>`；无作者的资料用 `<两位序号> <短标题> — <名称>`。破折号用全角 `—`，与库内既有笔记一致。
- frontmatter 固定键：`类型 / 状态 / zotero_key / doi / 优先级 / 阅读序 / pdf / tags`。状态取值：`未读 / 精读中 / 精读工作稿`。
- 正文顺序固定：论点句 H1 → `**论文**`（含出版商、DOI、Zotero 链接）→ `**已阅读范围**` → `## 核心结论与研究设计` → `## 核心证据与异常`（三列表格 + "不能外推的地方"）→ `## 项目应用` → `## 待读`。
- 页码/公式号/表号一律照 `docs/文献阅读清单.md` 抄录；DOI 只用清单给出的源，不另找替代源。
- `zotero_key` 与正文 `zotero://select/library/items/<key>` 必须同一条目；Wilhelm 一篇对应两个 Zotero 条目（会议论文 + 学位论文），frontmatter 存会议论文键。

## 4. 以后新增一篇：三步

1. **Zotero**：在集合 `越障仿真` 下建条目（DOI 走"添加条目 → 通过标识符添加"），放进 `必读` 或 `选读`，有 PDF 就拖到条目上；记下 item key。
2. **复制模板**：复制 `越障仿真/模板/文献精读模板.md` 到 `越障仿真/文献精读/`，按规则改名，填 frontmatter（`状态: 未读`、`zotero_key`、`doi`、`pdf`、`阅读序`）。
3. **登记**：在 `文献索引.md` 的阅读顺序里加一行 `- [ ] [[越障仿真/文献精读/…]] — [DOI](https://doi.org/…)`，并按需更新状态统计、缺 PDF/缺 DOI 分组。

## 5. 本地 API 写入是否可用：可用

- 环境：Zotero 10.0.9，本地 API `http://127.0.0.1:23119/api/users/0/`，`Zotero-API-Version: 3`。
- 写入需要三步授权（Zotero 10 起）：`GET /api/` 取 `Zotero-Server-ID` → `POST /api/local/authorize`（`{"appName": "..."}`）拿一次性/长期 key → 写请求带 `Zotero-Server-ID` + `Zotero-API-Key`。缺 Server-ID 返回 428，缺 key 返回 401。
- 已验证：创建集合、创建 13 条文献 + 2 条补充条目、批量写 tags/collections、用 `POST /items/<key>/file` 三段式上传 PDF，全部成功（HTTP 200/204）。
- 结论：不需要退路。本次未生成 `refs/文献库.ris`；RIS 导入方案仅在本地 API 不可用时启用：导出 RIS → Zotero 文件 → 导入 → 右键"新建集合"建 `越障仿真` 与两个子集合。
- 注意：key 与 Server-ID 属于本机凭据，不写进仓库；换机器或数据库后 Server-ID 会变，需重新读取并重新授权。

## 6. 已知缺口

- IEC 62849:2025 未购买全文，笔记只到证据表 §5.1.1 的摘录；Figure 4 的 S1/S2/S3 角度未读到。
- Choi 2017（Elsevier 付费）、Cui 2016（SAGE 返回 HTML）无本地 PDF；MuJoCo 文档为网页，无 PDF。
- 没有把 `refs/` 全量复制进 Obsidian 库；PDF 以 Zotero 附件为准，笔记 `pdf:` 字段保留仓库相对路径。
