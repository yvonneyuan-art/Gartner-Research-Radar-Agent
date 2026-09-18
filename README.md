# Gartner Research Radar Agent

一个只使用公开信息的 Gartner 周报 Agent。固定跟踪 **AI Infrastructure、Agentic AI、AI Security、Cloud、Virtualization、GPU、Kubernetes**；生成中文 HTML 周报，并向飞书发送摘要及报告链接。无需登录 Gartner。

默认部署：**GitHub Actions 每周运行 → GitHub Pages 托管 HTML → 飞书自定义机器人**。研究历史、周报归档及发送状态保存在独立 `radar-data` 分支，不依赖会过期的缓存。提供可复用 Skill 和飞书应用上传 HTML 文件模式。

## 当前交付状态

- 研究 runner、HTML 模板、配置模板、云端工作流、飞书两种适配器均已实现。
- 离线样例使用一项核实过的 Gartner 官方公开来源，明确标识“验证样例 · 非完整周报”。它不是完整的本周周报。
- 自动化测试覆盖来源校验、证据日期、跨周去重、引用过滤、HTML 转义、重复发送与失败状态。
- 首次生产运行需要 `TAVILY_API_KEY`、`OPENAI_API_KEY`；发送飞书还需要 `FEISHU_WEBHOOK_URL`。没有密钥时生产运行会明确失败，不会用样例冒充真实结果。

## 5 分钟本地验证

建议 Python 3.12。以下命令在项目根目录运行：

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m radar.runner generate --demo --as-of 2026-09-18 --data-dir data-demo
python -m http.server 8000 --directory data-demo/site
```

打开 `http://localhost:8000/2026-09-18.html`。模板独立、无外部字体、无 JavaScript、手机适配，可浏览器打印为 PDF。

## 生产运行

复制 `.env.example` 为 `.env` 并在本地编辑密钥。代码不会自动读取 `.env`，显式加载环境变量：

```sh
set -a
source .env
set +a
python -m radar.runner generate --data-dir data
```

输出：

| 路径 | 用途 |
|---|---|
| `data/site/YYYY-MM-DD.html` | 可发布的周报 |
| `data/site/index.html` | 历史归档 |
| `data/reports/YYYY-MM-DD.json` | 本期结构化数据及短元数据证据 |
| `data/latest.json` | 最新一次生成的数据 |
| `data/state.json` | 跨周去重及发送记录 |

将 `data/site` 发布为 HTTPS 网站后，发送飞书：

```sh
python -m radar.runner notify --data-dir data --as-of 2026-09-18 --base-url https://YOUR-OWNER.github.io/Gartner-Research-Radar-Agent
```

**推荐云端部署步骤见 [部署说明](docs/deployment.md)。** 部署流程会自动使用实际 Pages URL，支持项目路径及自定义域名，无需手工拼接。

## 周报结构

1. 本周核心判断，关联到具体来源。
2. 重点研究表格：主题、标题、日期、分析师、研究类型、访问状态、关注理由。
3. 七大主题的摘要与趋势分析；无发现的主题仍展示。
4. 跨主题信号，要求至少两项来源、覆盖两个主题。
5. 逐条公开摘要和目录转述、原文链接、证据级别。
6. 搜索覆盖、候选数量、处理上限、失败与缺口说明。

“付费/订阅”“公开免费”“未知”是全文访问状态；不会因摘要可见就推断全文免费。目录未公开则留空。趋势判断及“为什么值得关注”属于 Agent 推断，不代表 Gartner 官方立场。

## 研究与更新规则

默认按上海日期取结束日及此前六天；每个主题搜索本周与过去 30 天两个窗口（共 14 次 Tavily 搜索），每次最多 6 条候选，最多分析 40 个唯一页面。成本取决于搜索服务额度、模型及文本长度；失败重试可能增加调用次数。模型可通过 `OPENAI_MODEL` 更换，需支持 Chat Completions JSON mode。

只收录 Gartner 官方 document、newsroom 和 analyst blog 页面，研究类型分开显示。不将供应商宣传、Peer Insights 评论或用户上一轮生成的报告当作验证证据。Tavily 的公开文本提取和搜索摘要有不同标记；没有原文提取时仍可保留搜索线索，但需核实。所有页面内容视为不可信数据。

以文档 ID / 规范 URL 去重，去掉跟踪参数与片段。同一文档跨多个主题只保留一条。首次观察时间不等于发布日期；只有有证据的日期落在本期窗口内才计作“本周新增/更新”。旧报告标“补充背景”，无日期标“首次发现·日期未知”，无明确更新时间的元数据变化标“待核实”。相同条目不重复收录；模型改写或搜索摘要变化不算研究更新。更新发现依赖公开索引，未进入检索结果的旧页更新可能漏检。

标题来源于搜索结果；分析师需原文包含姓名，日期需引文能解析到同一天。字段证据匹配只是最低校验，不能证明模型语义判断完全正确；读者可打开原文复核。摘要与目录做简短中文转述，不公开抓取全文，不重建付费正文。原始搜索正文仅在进程内用于分析，不写入归档；仅短元数据证据随 JSON 保存。

## 重跑、失败与持久化

- 同一天已有报告则直接复用，不重新付费搜索。正式数据与样例数据必须分目录。
- 所有检索失败，或所有提取失败时退出非零，保留旧状态；部分失败仍生成报告，但显著标记覆盖不完整。
- 趋势综合失败时保留逐条研究、说明失败，不编造结论。
- 先保存状态与报告，再部署网页，再推送。部署失败可重跑继续；飞书失败不写成功记录。
- 飞书按期号、发送方式、目的会话做去重。Webhook 无幂等键：网络超时但服务端已接收，或发送成功后状态提交失败，再次手动重跑仍可能重复。为避免盲目重复，发送请求不自动重试；请先查看飞书群再重跑。应用模式另使用确定性 UUID。
- 公开仓库中的 `radar-data` 也是公开的，仅应保存公开研究数据。`site` 以外的 JSON 不会被 Pages 发布，但可从公开仓库读取。
- 分支持续保留旧周报，没有自动删除；需要控制存储量时可单独制定归档策略。不要删除 `state.json`，否则会失去去重历史。

## 飞书应用模式

配置 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_CHAT_ID`，并设置 GitHub Variable `FEISHU_MODE=app`。实现已包含 tenant token → `file_type=stream` 上传 HTML → 向指定 `chat_id` 发送 file 消息。需要应用启用机器人、具备文件上传和发消息权限，且已加入目标会话。

```sh
python -m radar.runner notify --data-dir data --as-of 2026-09-18 --mode app
```

飞书是否支持 HTML 在线预览由客户端决定；文件可下载后浏览器打开。云端默认流程仍发布 Pages，若只需要私有文件，可按部署说明禁用 Pages 步骤。

## Skill

`skills/gartner-research-radar/SKILL.md` 可复制到 Codex 或兼容 Agent 的 skills 目录。Skill 提供研究契约与 runner 调用方式；云端运行不依赖桌面 Codex 登录态。它需要本项目代码可访问，不是只复制一个 Markdown 就能获得后台定时运行。

## 项目结构

```text
.github/workflows/weekly.yml  每周研究、历史持久化、发布和发送
.github/workflows/test.yml    无密钥 CI 验证
radar/research.py             检索、证据校验、分类、趋势综合
radar/runner.py               CLI、HTML、状态与恢复
radar/delivery.py             飞书 webhook / 应用文件发送
radar/network.py              超时、有限重试、错误脱敏
radar/templates/              周报与归档 HTML 模板
skills/                      可复用研究 Skill
tests/                       自动化测试与单来源验证样例
config.json                  时间窗口、主题、模型与数量上限
.env.example                 仅环境变量名称，无密钥
```

## API 与部署参考

- [Tavily Search](https://docs.tavily.com/documentation/api-reference/endpoint/search)
- [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat)
- [GitHub Pages 自定义工作流](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [GitHub 定时触发](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [飞书自定义机器人](https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot)
- [飞书文件上传](https://open.feishu.cn/document/server-docs/im-v1/file/create)
- [飞书发送消息](https://open.feishu.cn/document/server-docs/im-v1/message/create)
- [样例的官方来源](https://www.gartner.com/en/documents/8377781)

此项目为独立工具，不隶属于 Gartner。公开检索不保证报告完整覆盖，也不替代订阅研究全文。
