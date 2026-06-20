# 首次使用：先配置你的模型 Agent

BLCaptain Opportunity PRD Skill 是 Codex 主持的机会挖掘工作流。Codex 负责主持、汇总、写文件和校验；外部模型 Agent 负责多视角讨论、反方审查、长文本理解和工程视角。

没有可用外部模型时，本 skill 不会进入机会分析，也不会声称完成多模型讨论。

## 支持的模型 Agent

| 类型 | 示例 | 推荐接入 | 常见职责 |
|---|---|---|---|
| OpenAI-compatible | DeepSeek、GLM、Gemini、Grok、自建网关 | `base_url` + `model` + `api_key_env` | 主分析、结构化、反方、外部趋势 |
| CLI Agent | Claude CLI、Claude Code、Composer、本地包装脚本 | 本机非交互 `command` | 长文本、反方、代码或原型视角 |
| 本地模型 | Ollama、本地推理脚本 | CLI | 低成本初筛、结构化辅助 |
| Codex | 当前 Codex 会话 | 内置主持 | 主持、冲突整合、文件生成、校验 |

Codex 不计入外部模型数量。

## 最简单方式

直接对 Codex 说：

```text
帮我接入 DeepSeek。我有 API Key，环境变量名用 DEEPSEEK_API_KEY。
```

或者：

```text
帮我接入 Claude CLI。本机非交互命令是：claude -p
```

Codex 应该只追问必要信息，并帮你生成本地模型池配置。

## 本地配置路径

推荐用户配置文件：

```text
~/.config/blcaptain-opportunity-prd/model-pool.json
```

仓库里的 `templates/model-pool.providers.example.json` 只是示例，不保存真实密钥。

## 安全要求

- 不要把真实 API Key、token、cookie 写进 JSON、README、Prompt 或 Git 仓库。
- 配置文件只保存环境变量名，例如 `DEEPSEEK_API_KEY`。
- 真实密钥放到系统环境变量、macOS Keychain、1Password、Bitwarden、本地私有 dotenv 或模型 CLI 登录态中。

## 验证

```bash
python3 scripts/setup_model_pool.py --doctor
python3 scripts/check_model_pool.py --config ~/.config/blcaptain-opportunity-prd/model-pool.json
```

通过健康检查后，才进入社区证据扫描、痛点分析、Gate 和 PRD 生成。
