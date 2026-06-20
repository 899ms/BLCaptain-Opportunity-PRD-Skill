# 模型 Agent 清单

本 skill 不绑定固定供应商。只要用户拥有可调用模型，并且能通过 OpenAI-compatible API 或本机 CLI 返回文本，就可以登记到模型池。

## 支持类型

| Agent 类型 | 可接入示例 | 配置字段 | 适合职责 |
|---|---|---|---|
| OpenAI-compatible | DeepSeek、GLM、Gemini、Grok、自建网关 | `base_url`、`model`、`secret_ref` | 主分析、结构化、商业反方、外部趋势 |
| 长文本 CLI | Claude CLI、Claude Code、本地长上下文模型 | `command` | 长评论理解、反向压力测试、综合审查 |
| 代码/原型 CLI | Composer、代码生成 CLI、本地脚本 | `command` | 工程可行性、原型视角、任务拆分 |
| 本地模型 CLI | Ollama、本地推理脚本 | `command` | 低成本初筛、隐私敏感样本本地处理 |
| Codex 主持 | 当前 Codex 会话 | 不需要外部配置 | 主持、整合、文件生成、校验、交接 |

## 动态分工

模型职责由健康检查结果和 `capability_tags` 决定，不按模型名称写死。

常见标签：

- `general`：通用分析
- `structure`：结构化整理
- `commercial_reverse`：商业反方
- `long_context`：长文本理解
- `external_trend`：外部趋势
- `social`：社交讨论视角
- `code`：代码或工程视角
- `cost_sensitive`：低成本任务

## 配置状态

| 可用外部模型数 | 状态 | 行为 |
|---:|---|---|
| 0 | `config_required` | 只输出配置引导，不进入机会分析 |
| 1 | `low_confidence` | 可低置信度初筛，不声称多模型讨论 |
| 2-3 | `standard` | 可做主分析、反方、结构化审查 |
| 4+ | `heavy_discussion` | 可做多视角讨论 |

## 硬约束

- Codex 主持能力不计入外部模型。
- 本机发现的 CLI 只算候选，不写入模型池并通过健康检查前，不参与讨论。
- 未经本 skill 模型池登记和健康检查的外部模型不能参与讨论。
- 输出中不得暴露真实密钥、token、cookie。
