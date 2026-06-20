# 模型配置状态

| 字段 | 内容 |
|---|---|
| 配置状态 | config_required / low_confidence / standard / heavy_discussion |
| 已配置外部模型数 | 0 |
| 外部模型通过数 | 0 |
| Codex 主持状态 | 可主持（不计入外部模型） |
| 降级说明 | 无可用外部模型时只输出配置引导 |

## 最简单配置方式

直接告诉 Codex：

```text
帮我接入 DeepSeek。
```

或：

```text
帮我接入 Claude CLI。本机非交互命令是：claude -p
```

Codex 会判断调用方式、生成或更新本地模型配置、提醒密钥安全，并运行健康检查。

## 手动配置引导

1. 添加模型：填写模型名称，例如 DeepSeek、GLM、Claude、Gemini、Grok、Local Model。
2. 填调用方式：OpenAI-compatible URL、CLI 命令或暂不确定。
3. 测试并选择用途：长文本、商业反方、结构化、外部趋势、代码实现或通用。

真实 API Key 不写入配置文件。API Key 模型优先使用 `scripts/setup_model_pool.py connect <model> --store auto --prompt-key` 保存到系统安全凭据，配置文件只写 `secret_ref`。环境变量、1Password、Bitwarden、dotenv 本地私有文件或模型 CLI 登录态是高级或兜底方式。

## 动态模型分工

| 模型 | 调用方式 | 健康状态 | 能力标签 | 本轮角色 | 分配依据 |
|---|---|---|---|---|---|

## 继续条件

- 通过至少 1 个外部模型健康检查后，才进入机会分析。
- 只有 1 个外部模型时，标注单模型低置信度，不声称完成多模型讨论。
