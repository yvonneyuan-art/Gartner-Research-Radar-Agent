# 仓库怎么配置：按这个顺序操作

仓库已经建好：[Gartner-Research-Radar-Agent](https://github.com/yvonneyuan-art/Gartner-Research-Radar-Agent)。不用再建服务器，也不用上传 Gartner 账号密码。

## Tavily 和 DeepSeek 分别做什么

Tavily 是给程序调用的联网搜索服务：按关键词找出 Gartner 的公开网页和摘要。DeepSeek 是模型服务：读取这些搜索结果，整理报告日期、分析师与中文分析。两者是不同服务，需要各自的 key；DeepSeek key 不能填入 Tavily 的配置项。Tavily 是当前实现选用的搜索后端，不是 Gartner 的账号或订阅。

本项目直接向 DeepSeek 官方 API 发请求，不需要 OpenAI 账号或 OpenAI key。默认模型为 `deepseek-flash`，可通过 `DEEPSEEK_MODEL` 覆盖。

## 第一步：把三个基础密钥填到 Secrets

直接打开 [仓库的 Actions Secrets 页面](https://github.com/yvonneyuan-art/Gartner-Research-Radar-Agent/settings/secrets/actions)。点击 **New repository secret**，分别添加下表三项。左边的 Name 原样复制，右边 Secret 填自己的值。

| Name | Secret 填什么 | 用途 |
|---|---|---|
| `TAVILY_API_KEY` | [Tavily 控制台](https://app.tavily.com/)生成的 API key | 每周搜索 Gartner 公开资料 |
| `DEEPSEEK_API_KEY` | [DeepSeek API 控制台](https://platform.deepseek.com/api_keys)创建的项目 API key | 提取日期/分析师及生成中文分析 |
| `FEISHU_WEBHOOK_URL` | 飞书目标群中自定义机器人的完整 webhook 地址 | 推送摘要及固定 HTML 链接 |

如果机器人启用了签名校验，再添加 `FEISHU_WEBHOOK_SECRET`，值是同一个机器人页面里的签名密钥。

这些值只能放 **Secrets**，不要填到 `config.json`、Variables、代码或聊天里。DeepSeek API 需要可用的 API 额度；这里填 DeepSeek 开放平台生成的 key，不是网页登录密码。

飞书入口：目标群 → 群设置 → 群机器人 → 添加机器人 → 自定义机器人。若设了关键词校验，用 `Gartner` 即可，发送文本包含该词。GitHub 托管 runner 的出口 IP 可能变化，签名校验更适合此部署。

## 第二步：检查 Variables（默认不用填）

[Actions Variables 页面](https://github.com/yvonneyuan-art/Gartner-Research-Radar-Agent/settings/variables/actions)：

| Name | 默认值 | 什么时候改 |
|---|---|---|
| `DEEPSEEK_MODEL` | `deepseek-flash`（来自 config） | 希望使用另一可用且支持 JSON mode 的模型 |
| `FEISHU_MODE` | `webhook` | 希望上传 HTML 文件时改为 `app` |

不需要设置 GitHub token，Actions 自带 `GITHUB_TOKEN`。工作流已经声明写入历史分支与 Pages 所需权限；若组织策略阻止，再由管理员调整。

## 第三步：启用网页托管

打开 [Settings → Pages](https://github.com/yvonneyuan-art/Gartner-Research-Radar-Agent/settings/pages)，Source 选择 **GitHub Actions**。

当前仓库保持私有。GitHub Pages 在私有仓库的可用性取决于账号套餐；如果设置页要求升级，不能只靠添加密钥解决。可以保留私有仓库并采用支持的套餐，或在确认可以公开代码后改为公开仓库。不要把“私有仓库”误认为“网页一定私有”：默认 Pages 网站是公开链接。

若不希望公开网页，可保留私有仓库并选择下面的飞书应用文件模式；需要调整默认工作流，跳过 Pages 三个步骤以及 job 的 Pages environment URL。这不是当前默认部署方式。

网页地址通常为 `https://yvonneyuan-art.github.io/Gartner-Research-Radar-Agent/`。本项目只有 `index.html`，以后每周仍然打开这个地址。飞书会附加 `#edition-日期`，只改变定位，不改变页面文件。

## 第四步：先手动跑一遍

打开 [Actions](https://github.com/yvonneyuan-art/Gartner-Research-Radar-Agent/actions) → **Weekly Gartner Research Radar** → **Run workflow** → 选 `main` → 再点 Run workflow。

第一次运行会导入本项目已经整理好的 **2026-08-19—2026-09-18、11 项研究**。如执行日期晚于 9 月 18 日，会接着补充新一期（需要检索和模型密钥）。相同日期重跑复用已有内容，避免重复生成/发送。

成功后检查三件事：

1. `Deploy HTML archive` 成功，页面能看到首期及新的追加内容。
2. 飞书群收到一条摘要，链接打开同一个 HTML 并定位到本期。
3. 仓库出现 `radar-data` 分支，保存 `reports/*.json`、`state.json`、`site/index.html`。

未配置 webhook 时，工作流会明确写“delivery not configured”，这只代表网页生成/发布完成，不代表飞书发送成功。全部检索失败会使工作流失败，部分失败会出现在本期覆盖说明里。

## 哪些配置已经替你写好了

| 位置 | 当前值/行为 |
|---|---|
| `config.json` → `initial_months` | 1，空历史回看一个日历月 |
| `window_days` | 7，正常每周扫描；漏跑自动补齐 |
| `lookback_days` | 30，捕获延迟索引与近期更新线索 |
| `results_per_query` | 8，每组词每个窗口的候选条数 |
| `initial_max_documents` / `max_documents` | 100 / 60，月度/周度处理上限 |
| `topics` | 八个主题，每主题两组同义词；无需你手工填写 |
| `excluded_primary_topics` | GPU、存储、备份容灾、桌面云、边缘云等排除方向 |
| `.github/workflows/weekly.yml` | 每周五北京时间 09:17；GitHub 高负载时可能延迟 |

研究数据来自公开索引，处理上限不是完整性保证。默认首轮约 16 次高级检索，周度约 32 次，最多分别 100/60 次逐条模型分析，另一次综合；失败重试可能增加调用。为 Tavily/DeepSeek 账户设置适合自己的预算。

## 可选：飞书直接收 HTML 文件

在飞书开放平台创建企业自建应用，启用机器人、完成相关权限审批/发布，把机器人加入目标会话。增加 Secrets：

- `FEISHU_APP_ID`：应用 ID。
- `FEISHU_APP_SECRET`：应用密钥。
- `FEISHU_CHAT_ID`：目标群 `chat_id`。

再将 Variable `FEISHU_MODE` 设为 `app`。实现流程是获取 tenant token → 以 stream 类型上传累计 `index.html` → 发 file 消息。权限通常包括 `im:resource` 和 `im:message:send_as_bot`，以飞书控制台实际要求为准。HTML 在线预览由客户端决定，可下载后在浏览器打开。默认工作流仍会先发布 Pages；如选择完全私有文件路径，需要按第三步调整。

## 故障与恢复

- 缺 key/401：检查 Secret 名字、所属仓库、有效期和 API 额度。
- 429/5xx：检索与模型有限重试，仍失败则记录缺口/停止。飞书发送不盲目重试。
- Pages 要求升级：账号套餐问题，与 API key 无关。
- 数据分支推送失败：检查仓库 Actions 写权限及 `radar-data` 分支规则；不要删除历史。
- 飞书失败：检查机器人签名、关键词、群成员或应用权限。业务失败不会记为成功。
- 飞书超时但群已收到：发送结果可能不确定；重跑前先确认，Webhook 无严格幂等保证。
- 同一天没有新搜索：这是期号复用机制，不是定时器失效。

## 官方说明

- [GitHub Secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
- [GitHub Pages 设置](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [GitHub 定时触发](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [DeepSeek API key](https://api-docs.deepseek.com/zh-cn/)
- [Tavily Search API](https://docs.tavily.com/documentation/api-reference/endpoint/search)
- [飞书自定义机器人](https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot)
- [飞书上传文件](https://open.feishu.cn/document/server-docs/im-v1/file/create)
- [飞书发送消息](https://open.feishu.cn/document/server-docs/im-v1/message/create)
