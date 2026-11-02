# Cloudflare Pages 迁移

现有定时研究仍由 GitHub Actions 执行，每周一北京时间 09:00 开始。Cloudflare 只托管生成的 HTML。新网址使用项目名称，不包含 GitHub 用户名。

已于 2026-11-02 完成部署与公开页面一致性验证。本次只刷新发布，未重复发送飞书。

## 首次配置

1. 登录 Cloudflare，在 Workers & Pages 创建 Pages 项目，选择 Direct Upload，本站已创建项目 `enterprise-research-weekly`，生产分支为 `main`。公开入口：[Gartner 周报](https://enterprise-research-weekly.pages.dev/)。
2. 创建 API Token：仅授予目标账户的 `Account → Cloudflare Pages → Edit` 权限。
3. 在 GitHub 仓库 Settings → Secrets and variables → Actions 添加 Secrets：`CLOUDFLARE_ACCOUNT_ID`、`CLOUDFLARE_API_TOKEN`。不要在聊天、代码或文档中记录密钥值。
4. 添加 Variables：`CLOUDFLARE_PROJECT_NAME` 填实际项目名称；准备好后将 `HOSTING_PROVIDER` 设置为 `cloudflare`。
5. 手动运行 Weekly Gartner Research Radar，勾选 `refresh_only`。这会将已有历史重新发布，不重新检索、不调用模型、不重复发送飞书。
6. 工作流会读取 Cloudflare 分配的正式域名，并确认该网址的 HTML 与本次生成内容一致。验证成功后，以后的每周推送自动使用新网址。

## 切换与回退

未设置 `HOSTING_PROVIDER` 时仍使用原来的 GitHub Pages，避免登录与配置期间中断运行。新网址验证通过后再决定是否关闭旧网页或修改仓库可见性；本迁移不会自动修改可见性。

如需回退，将 `HOSTING_PROVIDER` 改为 `github`，再运行一次 `refresh_only`。前提是原 GitHub Pages 尚未关闭。

新网址用于对外分享；现有公开仓库本身仍可被检索。隐藏仓库需要另行切换为私有。
