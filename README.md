# Gartner Research Radar Agent

**一个 HTML，持续追加。** 首期回看近一个月，此后在同一个 `index.html` 的核心判断、主题进展和跨主题趋势模块内追加内容，从新到老排列。研究汇总按规范 URL 去重，每篇仅保留一份完整摘要及原文链接，按发布日期降序排列，未知日期按首次收录日期排列。飞书始终发送同一个页面链接，并带本期定位锚点。仅检索公开信息，不登录 Gartner。

## 当前范围

| 主题 | 重点关键词/产品关联 |
|---|---|
| Cloud / Private & Hybrid | Private Cloud、Hybrid Cloud、Distributed Hybrid Infrastructure、Sovereign Cloud、Cloud Repatriation；Cloud/ZCF |
| Virtualization | Server Virtualization、Hypervisor、VMware Alternative、VM Migration；ZSphere/ZVF |
| HCI | Hyperconverged Infrastructure、Full-stack Infrastructure、Integrated Systems；超融合 |
| Kubernetes | Container Management、Platform Engineering、KubeVirt、Internal Developer Platform；Zaku |
| Cloud Management & FinOps | CMP、Hybrid Cloud Operations、AIOps、FinOps、AI FinOps、Token Cost；多云运营与成本治理 |
| AI Infrastructure | Private AI、Enterprise AI Platform、Model Serving、Inference Platform、MLOps/LLMOps；AIOS |
| Agentic AI | Agent Runtime、Agent Orchestration、Multiagent、AI Agents for I&O；企业智能体运行与运维 |
| AI Security | AI TRiSM、AI Governance、AI Gateway、Model Gateway、Agent Identity、Runtime Controls；Zentrix |

按用户要求，不单独跟踪 GPU、存储、备份容灾、桌面云、边缘云、数据库等其他产品方向。它们作为相关平台研究中的附带内容可能出现，但不会据此新增专题。

产品线映射参考 [ZStack 官方产品矩阵](https://www.zstack.io/)，具体研究归纳是本工具的推断，非 Gartner 对产品的评价。详细配置见 [关键词说明](docs/topics.md)。

## 已交付的首期

[直接打开持续研究笔记](examples/index.html)：**2026-08-19—2026-09-18**，11 项 Gartner 官方公开研究/新闻稿，含日期、分析师、摘要、目录转述、原文与关注理由。这是真实公开资料整理，不是虚构排版样例；并不声称覆盖 Gartner 全库。首期结构化数据在 `bootstrap/2026-09-18.json`。

默认云端工作流首次发现空历史时导入这份基线，再补充运行日对应的新一期。后续继续沿用去重历史。没有基线的全新本地运行自动回看一个日历月；有历史时默认扫描近七天，漏跑时从上一期之后补齐日期。

## 页面行为

- 全站只有 `site/index.html`，不再生成每周一个 HTML；每期 JSON 是内部数据，不是阅读页面。
- 新内容按期号追加，重跑同一期不重复。历史期的 HTML 锚点包含期号，同一报告更新后也不会造成链接冲突。
- 独立主题框只展示本期有确认新增/更新研究的主题。只有旧背景、日期不明、元数据待核实的主题不占框。
- 期末一句话汇总无新增的主题；检索失败会注明，不能把失败说成“没有发布”。
- 表格和来源区仍保留必要的背景或待核实线索，并显著标记其状态。
- 网页每次从历史 JSON 重建，并以原子替换更新 `index.html`；已有旧格式数据会迁移，移除旧的日期 HTML。

## 本地使用

建议 Python 3.12：

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
# 先导入已经整理好的首期，不需要 API 密钥
python -m radar.runner import-report --input bootstrap/2026-09-18.json --data-dir data
python -m http.server 8000 --directory data/site
```

访问 `http://localhost:8000/`。导入只允许空历史，避免覆盖已有期号与发送状态。

后续自动研究需要 API 密钥：复制 `.env.example` 为 `.env`，自行填入并加载：

```sh
set -a
source .env
set +a
python -m radar.runner generate --data-dir data
```

同一天已有报告则复用；未来新日期才会继续研究。无 API 密钥时不会用样例冒充结果。离线测试模式仍可用 `generate --demo --as-of 2026-09-18 --data-dir data-demo`，但不能将 demo 推送为正式周报。

## 搜索与模型

Tavily 负责联网发现 Gartner 公开网页；DeepSeek 负责元数据提取与中文分析。两者凭据分别为 `TAVILY_API_KEY` 和 `DEEPSEEK_API_KEY`。模型请求直接发往 `https://api.deepseek.com/chat/completions`，默认 `deepseek-flash`（可用 `DEEPSEEK_MODEL` 覆盖），无需 OpenAI key。

## 云端与飞书

默认 **GitHub Actions → GitHub Pages → 飞书 webhook**，每周一北京时间 09:00，无常驻服务器。配置步骤见 [逐步配置指南](docs/deployment.md)。

| 配置位置 | 内容 |
|---|---|
| Actions Secrets | 检索、模型和飞书密钥 |
| Actions Variables | 可选模型名、飞书发送模式 |
| `config.json` | 主题、同义词、时间窗口、处理上限 |
| `.github/workflows/weekly.yml` | 定时计划 |
| `radar-data` 分支 | 历史 JSON、去重记录、唯一 HTML |

发布后：

```sh
python -m radar.runner notify --data-dir data --as-of 2026-09-18 --base-url https://OWNER.github.io/Gartner-Research-Radar-Agent
```

链接为 `/index.html#edition-2026-09-18`。可选应用模式上传的是同一个累计 HTML，使用 `notify --mode app`；配置 app_id/app_secret/chat_id 环境变量即可。文件能否在线预览由飞书客户端决定。

## 证据、成本和恢复

官方 document、newsroom 和 analyst blog 是研究来源；不把 Peer Insights 评论或用户先前生成的文本当作验证材料。分析师与日期进行短引文匹配，未知字段保留未知。公开摘要不代表全文免费；不抓取付费正文。模型输出仍需要必要的人工复核。

每主题两组同义词：初始月度扫描通常 16 次高级搜索；每周扫描和回溯共 32 次，漏跑补齐超过回溯窗口时只查补齐窗口。候选上限初始 100 项、每周 60 项，每项一次抽取，另一次趋势综合。重试可能增加调用；API 按各自账户额度计费。

文档 ID/规范 URL 用于跨主题、跨期去重。只有明确的新发布时间/更新时间才记为本期新增/更新；模型改写不算研究更新。公开索引可能漏检旧页面更新，不能保证穷尽。

全部检索或提取失败时不写新报告；部分失败会标记缺口。先保存报告，再发布网页，再发送飞书。失败发送不记为成功；Webhook 无幂等键，网络结果不明或发送后状态提交失败可能导致重跑重复，需先看群里是否收到。历史状态不用短期缓存，持久化到 `radar-data`。

## Skill 与文件

`skills/gartner-research-radar/SKILL.md` 可复用到支持 Skill 的 Agent，配合本项目 runner 使用。

```text
radar/research.py               发现、元数据证据、分类、趋势
radar/runner.py                 月度初始化、每周追加、状态、发送
radar/templates/notebook.html   单一累计 HTML 外壳
radar/templates/edition.html    每期内容模板
radar/delivery.py               飞书 webhook 与应用上传
bootstrap/2026-09-18.json        已核对的首期公开数据
examples/index.html             可直接阅读的首期
config.json                    非敏感配置
.env.example                   环境变量模板
.github/workflows/weekly.yml    生产定时流程
.github/workflows/test.yml      无密钥 CI 测试
```

来源与 API 文档见部署指南。此工具独立于 Gartner，不代表其官方意见。

### 仅更新排版

在 Actions 手动运行时勾选 `refresh_only`，使用已保存的研究重建并部署页面，不搜索、不调用模型、不重复推送。原始每期 JSON 保留用于追溯；页面按模块合并，不再逐期堆叠整篇周报。各模块最新一期有新增内容的日期后标记“本周新增”；研究汇总中首次收录于最新一期的条目也在日期后标记“本周新增”。历史条目不显示状态标签。
