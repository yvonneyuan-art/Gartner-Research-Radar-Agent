# 云端部署与运维

## 推荐：GitHub Actions + GitHub Pages

无需常驻服务器。默认每周五 **09:17（Asia/Shanghai）**运行，也可手动执行。GitHub 定时任务可能排队延迟；只在默认分支触发。公开仓库长期无活动可能被暂停定时任务，请留意 GitHub 通知。

### 1. 创建仓库并上传项目

仓库名称：`Gartner-Research-Radar-Agent`。可以在 GitHub 网页新建仓库，再上传本项目（包括隐藏的 `.github` 目录）。使用命令行时：

```sh
git init -b main
git add .
git commit -m 'Build public Gartner research radar agent'
gh repo create Gartner-Research-Radar-Agent --public --source . --remote origin --push
```

若需要私有仓库，改用 `--private`。GitHub Pages 在私有仓库中的可用性取决于账户套餐。公开 Pages 上只发布公开研究摘要，任何获得链接的人都能访问；私有代码库不一定意味着私有网页。

### 2. 添加 Secrets

仓库 → Settings → Secrets and variables → Actions → New repository secret：

| Secret | 是否必需 | 来源/用途 |
|---|---|---|
| `TAVILY_API_KEY` | 是 | Tavily 控制台；公开搜索及文本提取 |
| `OPENAI_API_KEY` | 是 | OpenAI API 项目；抽取与中文趋势分析 |
| `FEISHU_WEBHOOK_URL` | webhook 推送必需 | 飞书群的自定义机器人完整 webhook |
| `FEISHU_WEBHOOK_SECRET` | 开启签名时必需 | 同一机器人的签名校验密钥 |
| `FEISHU_APP_ID` | 应用模式 | 飞书自建应用 ID |
| `FEISHU_APP_SECRET` | 应用模式 | 飞书应用密钥 |
| `FEISHU_CHAT_ID` | 应用模式 | 机器人已加入的目标会话 ID |

可选 Variables：`OPENAI_MODEL`（默认 config 中的模型），`FEISHU_MODE`（`webhook` 或 `app`）。Secret 值由工作流注入环境变量，配置文件和代码只保存名称。不要把 `.env` 提交到仓库。

默认无飞书 webhook 时，网页仍发布成功，但工作流摘要会明确写“Feishu delivery not configured”。这不代表消息已发送。

### 3. 开启 Pages 和写权限

- Settings → Pages → Build and deployment → Source 选 **GitHub Actions**。
- Settings → Actions → General 中允许 Actions；确保仓库策略允许工作流 `contents: write`，否则无法维护 `radar-data`。
- 工作流使用 `github-pages` environment。若组织设置了人工审批，需由管理员允许无人值守部署。
- 默认分支保护不必放宽。自动生成数据写独立 `radar-data` 分支；如组织规则保护所有分支，需要为该分支允许机器人写入。

### 4. 配置飞书机器人

群设置 → 群机器人 → 添加机器人 → 自定义机器人。开启签名校验，并将 webhook 与签名密钥填入 GitHub Secrets。若使用关键词校验，关键词可设为 `Gartner`。不推荐使用固定 IP 白名单，因为 GitHub 托管 runner 出口可能变化。

Webhook 默认只发一条文本：时间窗口、条目数量、核心判断、完整 HTML 链接。签名按飞书协议计算：以 `timestamp + 换行 + secret` 为 HMAC key，对空消息执行 SHA-256，再 Base64。校验 HTTP 状态及 JSON 中的业务错误码。

### 5. 首次手动运行

Actions → **Weekly Gartner Research Radar** → Run workflow。检查：

1. 无密钥测试通过。
2. `Research and render` 产生真实本期记录或明确无发现报告。
3. `radar-data` 分支有 `site/`、`reports/`、`state.json`。
4. `Deploy HTML archive` 成功，environment 提供实际访问链接。
5. 飞书群收到摘要及本期链接；点击可打开。

默认地址形式：`https://OWNER.github.io/Gartner-Research-Radar-Agent/`，本期为 `YYYY-MM-DD.html`。工作流实际使用部署步骤返回的 URL，不依赖这个假设。

## 应用上传 HTML

飞书开放平台新建企业自建应用，启用机器人，开通并发布文件上传及机器人发送消息所需权限；权限项以开放平台控制台提示为准（通常包括 `im:resource`、`im:message:send_as_bot`）。把机器人加入目标群，配置应用 Secrets，并设置 `FEISHU_MODE=app`。

代码从 `tenant_access_token/internal` 获取短期 token，上传 `.html` 为 `stream`，再发送文件消息。不会写 token 到磁盘。此适配器已实现并有错误处理，但仍需用真实应用进行端到端联调。

若希望完全私有：使用私有仓库，保留报告生成、状态提交、Actions artifact 和应用发送；移除 `configure-pages`、`upload-pages-artifact`、`deploy-pages`，将 webhook 模式改为 app，删除 job 的 Pages environment URL 和多余 Pages 权限。应用模式不需要 `--base-url`。此为可选修改路径，默认工作流仍面向公开 HTML 链接。

## 故障处理

| 现象 | 处理 |
|---|---|
| 缺 API key / 401 | 检查 Secrets 名称、密钥权限和额度，切勿将密钥贴入日志 |
| 429 / 5xx | 检索/模型调用最多重试两次；仍失败则记录缺口或退出，检查服务状态/额度 |
| 公开正文提取不到 | 保留“搜索摘要”标记；不登录或绕过限制。目录和姓名无法确认就留空 |
| 无新报告 | 阅读覆盖状态；“无发现”不等于“没有发布” |
| Pages 部署失败 | 检查 Source=Actions、账户套餐、environment 和 pages/id-token 权限 |
| 数据分支写入失败 | 检查 contents 写权限及分支规则。不要删除历史分支来解决权限问题 |
| 飞书业务码非零 | 检查签名、机器人关键词、会话成员与权限；不会保存为发送成功 |
| 飞书发送超时 | 先检查群里是否收到，再手动重跑，避免不确定状态下重复通知 |
| 同一天重跑没有新搜索 | 这是恢复机制：复用已保存期号。需要更正时先备份并人工处理本期报告/状态，不能盲删全量历史 |

GitHub 运行失败通知由账户的 Actions 通知设置控制；本项目不使用出错的 webhook 再发送“失败通知”。HTML 上会显示部分失败原因，全部失败则让工作流失败。

## 成本与限制

默认每期 14 次高级搜索、最多 40 次逐页模型抽取、1 次趋势综合；重试可能增加调用，服务按各自账户计费。数量上限可在 config 修改。公共索引可能遗漏本周报告、旧页面更新或延迟收录内容；第一阶段并非 Gartner 订阅内容的完整同步器。

配置默认每周一次，无需常驻服务。更高可靠性或严格固定时间要求可把同一命令放入 Cloud Run Jobs / 云函数定时任务，另以对象存储保存 `data`，但这不是本项目的默认部署方案。
