# 机会评估报告：AI 客服质检报告

## 决策

| 字段 | 内容 |
|---|---|
| 结论 | Go |
| 置信度 | 中 |
| 一句话理由 | 近 30 天内多个社区出现客服主管手动抽检、截图培训和付费工具过贵的证据，反向证据可通过小切口质检报告回应。 |
| 下一步 | 生成商业化机会 PRD，并用 7 天实验验证付费意愿。 |

## 评论证据墙

| evidence_id | 平台 | 日期 | URL | 用户原话 | 行为信号 | 商业信号 | 等级 |
|---|---|---|---|---|---|---|---|
| E-001 | 小红书商家评论 | 2026-06-12 | https://example.com/xhs/customer-service/e001 | 每天只能抽几条客服聊天看，漏掉的问题月底才发现。 | 手动抽检聊天记录 | 成本节省 | A |
| E-002 | V2EX | 2026-06-11 | https://example.com/v2ex/customer-service/e002 | 我们现在靠截图给新人复盘，整理一次要半天。 | 手动截图培训 | 成本节省 | A |
| E-003 | Reddit smallbusiness | 2026-06-10 | https://example.com/reddit/customer-service/e003 | I stopped paying for the QA suite because it was too expensive for our small team. | 弃用竞品 | 弃用竞品 | A |
| E-004 | 知乎评论 | 2026-06-08 | https://example.com/zhihu/customer-service/e004 | 客服主管最麻烦的是不知道哪些对话值得复盘。 | 手动筛选复盘样本 | 购买意图 | A |
| E-005 | Product Hunt 竞品评价 | 2026-06-06 | https://example.com/producthunt/customer-service/e005 | Good product, but setup is too heavy when all I need is a weekly QA report. | 寻找轻量替代 | 付费抱怨 | A |

## 反向证据墙

| reverse_id | 来源 | 日期 | URL | 反向证据 | 回应 | 结论 |
|---|---|---|---|---|---|---|
| R-001 | 竞品文档 | 2026-06-12 | https://example.com/competitor/docs/r001 | 部分客服系统内置质检。 | P0 不做全客服系统，只做跨平台对话质检报告。 | 可回应 |
| R-002 | 商家访谈摘录 | 2026-06-10 | https://example.com/interview/r002 | 小商家预算有限。 | 先验证低价月付或一次性报告，不做大 SaaS。 | 可回应 |
| R-003 | 合规讨论 | 2026-06-09 | https://example.com/compliance/r003 | 客服对话包含隐私信息。 | P0 用脱敏 CSV 样例，不接生产系统。 | 可回应 |

# 商业化机会 PRD

## 0. 商业速读卡

| 字段 | 内容 |
|---|---|
| 产品一句话 | 给中小电商客服主管的轻量 AI 质检报告工具 |
| 目标用户 | 中小电商客服主管 |
| 核心痛点 | 抽检覆盖低、复盘慢、培训材料靠人工整理 |
| 商业信号 | 成本节省、弃用竞品、购买意图、付费抱怨 |
| P0 | 导入对话、自动打标签、生成质检报告 |
| 7 天实验 | 让 5 个客服主管看报告样例，至少 3 人愿意试用，至少 1 人愿意报价或付费 |

## Gate 结果

| Gate | 结果 | 证据 |
|---|---|---|
| G0 多模型配置 | pass | 单模型低置信度或标准模式均可运行 |
| G1 意图消歧 | pass | 目标用户、场景、商业目标明确 |
| G2 平台路由 | pass | 小红书、V2EX、Reddit、知乎、Product Hunt |
| G3 证据墙 | pass | 5 条有效证据，来自 5 类社区 |
| G4 数据可信度 | pass | 有效证据占比超过 30% |
| G5 商业信号 | pass | E-001、E-003、E-004、E-005 |
| G6 反向证据 | pass | R-001、R-002、R-003 均可回应 |
| G7 MVP 可验证 | pass | 7 天可用报告样例测试 |
| G8 PRD 可交接 | pass | P0 均绑定 evidence_id，有 3 条验收剧本 |

## 6. MVP 功能边界

| 用户故事 | evidence_id | 验收标准 | 不做什么 |
|---|---|---|---|
| 导入脱敏客服对话 CSV | E-001, E-002 | 能导入 100 条样例对话并显示解析结果 | 不接真实客服系统 |
| 自动给对话打质检标签 | E-001, E-004 | 输出服务态度、响应慢、未解决三类标签 | 不做复杂规则引擎 |
| 生成一页质检报告 | E-002, E-005 | 主管能看到 Top 问题、样例对话和培训建议 | 不做团队绩效系统 |

## 10. 7 天验证计划

| 假设 | 实验动作 | 通过标准 | 停止标准 |
|---|---|---|---|
| 痛点强度 | 找 5 个客服主管看报告样例 | 3 人承认正在手动抽检或截图培训 | 少于 2 人有同类痛点 |
| 付费意愿 | 展示月付价格或一次性报告价格 | 至少 1 人愿意报价或预付 | 只有口头说可以试试 |
| 技术可行 | 用脱敏 CSV 跑出报告 | 3 分钟内完成导入和报告生成 | 需要接生产系统才能演示 |

## 11. 风险、反证与停止条件

| reverse_id | 风险 | 回应 | 停止条件 |
|---|---|---|---|
| R-001 | 大客服系统内置质检 | 聚焦跨平台轻量报告 | 免费内置功能足够好 |
| R-002 | 小商家预算有限 | 验证低价报告 | 无人愿意报价 |
| R-003 | 隐私合规 | 使用脱敏 CSV | 用户要求接生产数据 |

## 12. AI 开发者交接说明

先实现脱敏 CSV 导入、三类标签和一页报告。不要扩展成完整客服系统。可以自由优化报告排版和标签文案，但不能删除 evidence_id 和停止条件。

## 13. 工程实施方案

### 系统架构

| 模块 | 职责 | 输入 | 输出 |
|---|---|---|---|
| Web 控制台 | 导入样本、展示报告、导出结果 | CSV、用户操作 | 报告页、导出文件 |
| API 服务 | 鉴权、导入、任务、报告查询 | HTTP 请求 | JSON、错误码 |
| Analysis Worker | 规则和 LLM 风险分析 | 对话批次 | RiskFinding |
| Report Exporter | 生成 Markdown/CSV | 风险结果 | WeeklyReport |

### 数据流

1. 用户上传脱敏 CSV，系统创建 ImportBatch。
2. Parser 生成 Conversation，Worker 运行规则和 LLM fallback。
3. 风险标注写入 RiskFinding，包含置信度和证据片段。
4. Report Exporter 生成 WeeklyReport 并支持导出。

### 技术选型

| 层级 | P0 选择 | 理由 |
|---|---|---|
| 前端 | Web 控制台 | 最快验证导入和报告价值 |
| 后端 | API 服务 + Worker | 避免分析任务阻塞请求 |
| AI | 规则优先 + LLM fallback | 控制成本并保留解释性 |
| 导出 | Markdown/CSV | 满足团队复盘 |

### AI 风险标注方案

| 项 | 内容 |
|---|---|
| 标签体系 | response_delay、unresolved_issue、negative_tone、training_example |
| 置信度 | confidence 低于 0.7 进入人工复核 |
| 成本上限 | 单批 LLM 成本上限 3 元，超限降级为规则优先 |
| 低置信度处理 | 不计入自动高风险统计 |

## 14. 数据模型与字段字典

| 实体 | 字段 | 类型 | 来源 | 是否必填 | 保留策略 | 说明 |
|---|---|---|---|---|---|---|
| ImportBatch | import_id | string | 系统生成 | 是 | 长期保留元数据 | 导入批次 |
| Conversation | conversation_id | string | 系统生成 | 是 | 原始文本 7 天删除 | 单条对话 |
| RiskFinding | confidence | number | 规则或 LLM | 是 | 报告保留 30 天 | 风险置信度 |
| WeeklyReport | report_id | string | 系统生成 | 是 | 30 天后删除 | 周报 ID |
| AuditLog | action | enum | 系统记录 | 是 | 180 天 | import、analyze、export、delete |

## 15. API 契约

| 接口 | 方法 | 请求字段 | 响应字段 | 错误码 | 权限 |
|---|---|---|---|---|---|
| /api/imports | POST | file、channel | import_id、status | INVALID_FILE_FORMAT、FILE_TOO_LARGE、EMPTY_CONVERSATION | workspace_member |
| /api/analysis-jobs | POST | import_id | job_id、status | IMPORT_NOT_READY、COST_LIMIT_EXCEEDED、ANALYSIS_TIMEOUT | workspace_member |
| /api/reports/{report_id}/export | GET | format | download_url | REPORT_NOT_FOUND、EXPORT_FAILED、DATA_RETENTION_EXPIRED | workspace_member |

## 16. 权限、安全、隐私与合规

| 主题 | P0 要求 | 验收方式 |
|---|---|---|
| 权限 | member 可导入和导出，admin 可删除 | 非授权请求返回 403 |
| 删除策略 | 原始对话默认 7 天删除 | 清理任务可验证 deleted 状态 |
| 审计日志 | import、analyze、export、delete 都记录 | 可查询 actor、action、target_id |
| 隐私 | 导出前遮罩手机号、邮箱、订单号 | 导出文件不含原始敏感值 |

## 17. 非功能需求

| 类型 | 指标 | 验收方式 |
|---|---|---|
| 性能 | 20 条对话 30 秒内完成报告 | 固定样本压测 |
| 容量 | 单批最多 1000 条对话，文件 10MB | 边界文件测试 |
| 成本 | 单批 LLM 成本上限 3 元 | mock 成本计数触发降级 |

## 18. 异常流程和边界条件

| 场景 | 系统行为 | 用户提示 |
|---|---|---|
| 导入格式错误 | 拒绝入库 | 文件格式不支持 |
| 空数据 | 不创建分析任务 | 未识别到有效对话 |
| 低置信度 | 进入人工复核 | 结果需人工确认 |
| 导出失败 | 保留报告并允许重试 | 导出失败，请重试 |

## 19. 测试方案和验收标准

| 测试类型 | 覆盖范围 | 通过标准 |
|---|---|---|
| 单元测试 | 解析、脱敏、规则标签、删除策略 | 关键分支通过 |
| 集成测试 | 导入到导出链路 | 固定样本全通过 |
| 端到端验收 | 三条验收剧本 | 用户路径无阻断 |

## 20. 部署运维与监控

| 项 | P0 要求 |
|---|---|
| 部署方式 | API 服务 + Worker + 元数据库 |
| 监控 | import_success_rate、analysis_duration、export_success_rate |
| 告警 | 分析失败率超过 10% 告警 |
| 回滚 | 规则和提示词版本化，可回滚上一版 |

## 21. 埋点与验证指标

| 事件 | 触发时机 | 属性 | 用途 |
|---|---|---|---|
| import_completed | 解析完成 | parsed_count | 判断样本质量 |
| report_generated | 周报生成 | risk_count | 判断核心价值 |
| export_clicked | 用户导出 | format | 判断报告可用性 |

## 22. 开发任务拆分与 DoD

| 任务 | 输入 | 输出 | DoD |
|---|---|---|---|
| T1 导入解析 | CSV | Conversation | 格式错误和空数据测试通过 |
| T2 风险标注 | Conversation | RiskFinding | 规则、LLM fallback、低置信度均有测试 |
| T3 报告导出 | RiskFinding | WeeklyReport | Markdown/CSV 导出通过验收剧本 |

## 验收剧本

验收剧本 1：上传脱敏 CSV 后，页面显示导入条数和解析状态。
验收剧本 2：点击生成质检报告后，报告包含 Top 问题、样例对话和培训建议。
验收剧本 3：搜索每个 P0 用户故事，都能找到对应 evidence_id。
