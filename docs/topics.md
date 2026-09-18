# 关键词与产品覆盖

最终采用八个主题；不是给每个关键词建一个页面框。只有有本期新增/更新的主题才显示独立章节。

| 主题 | 为什么补充这些关键词 |
|---|---|
| 私有云/混合云 | 仅搜 Cloud 容易偏向公有云。以 Private Cloud、On-premises Cloud 为主，加入 Hybrid Cloud、Distributed Hybrid Infrastructure、Cloud Repatriation 捕获混合管理与工作负载回迁；Sovereign Cloud 捕获控制权与本地部署议题，不等同于国内信创认证。 |
| 虚拟化 | Server Virtualization、Hypervisor 是市场术语；VMware Alternative、VM Migration 补足替代和迁移决策。 |
| 超融合 | 除 HCI 外加入全栈基础设施和集成系统术语；没有新研究时不单独展示。 |
| 容器/云原生 | Container Management 是 Gartner 常用研究类别；Platform Engineering、IDP、KubeVirt 补充平台运营和虚拟机/容器融合视角。 |
| 多云管理/FinOps | CMP 之外增加 Hybrid Cloud Operations、AIOps；FinOps/AI FinOps、Token Cost 分别观察基础资源和模型调用经济性。 |
| AI Infrastructure | 私有化 AI 平台、Model Serving、Inference Platform、MLOps、LLMOps 比单独 GPU 更贴近软件平台能力。 |
| Agentic AI | Runtime、Orchestration、Multiagent 和 I&O 场景帮助从智能体热词转向实际运行与运营需求。 |
| AI Security | AI TRiSM、模型/AI 网关、Agent Identity、Runtime Controls 连接 Zentrix 的调用治理、身份权限、运行时审计与成本约束；具体能力映射属于产品分析。 |

明确排除独立的 GPU 硬件市场、存储、备份、容灾、桌面虚拟化、边缘云、数据库与网络产品研究。平台型报告中的附带章节可以保留，但不会扩展为这些专题。

`config.json` 中 `topics` 的每个值是检索词组列表。每组内的引号短语以 OR 联合查询；不同组独立检索，然后统一去重。主题匹配由语义抽取完成，正文提到一个词不自动等于该主题。`excluded_primary_topics` 传给抽取器，剔除以排除方向为主要内容的结果。

参考：[ZStack 官方产品矩阵](https://www.zstack.io/)、[虚拟化关键能力公开目录](https://www.gartner.com/en/documents/8381581)、[分布式混合基础设施研究](https://www.gartner.com/en/documents/8345417)、[容器管理关键能力](https://www.gartner.com/en/documents/8353849)。
