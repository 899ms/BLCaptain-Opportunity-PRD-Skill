# 首次使用：先配置你的模型 Agent

BLCaptain Opportunity PRD Skill 是 Codex 主持的机会挖掘工作流。Codex 负责主持、汇总、写文件和校验；外部模型 Agent 负责多视角讨论、反方审查、长文本理解和工程视角。

没有可用外部模型时，本 skill 不会进入机会分析，也不会声称完成多模型讨论。

## 支持的模型 Agent

| 类型 | 示例 | 推荐接入 | 常见职责 |
|---|---|---|---|
| OpenAI-compatible | DeepSeek、GLM、Gemini、Grok、自建网关 | 直接接入 + 系统安全凭据 | 主分析、结构化、反方、外部趋势 |
| CLI Agent | Claude CLI、Claude Code、Composer、本地包装脚本 | 本机非交互 `command` | 长文本、反方、代码或原型视角 |
| 本地模型 | Ollama、本地推理脚本 | CLI | 低成本初筛、结构化辅助 |
| Codex | 当前 Codex 会话 | 内置主持 | 主持、冲突整合、文件生成、校验 |

Codex 不计入外部模型数量。

## 最简单方式

直接对 Codex 说：

```text
帮我接入 DeepSeek。
```

或者：

```text
帮我接入 Claude CLI。本机非交互命令是：claude -p
```

Codex 应该只追问必要信息，并帮你生成本地模型池配置。

如果是 API Key 模型，推荐使用隐藏输入：

```bash
python3 scripts/setup_model_pool.py connect deepseek --store auto --prompt-key
```

`--store auto` 会按系统自动选择安全存储：

- macOS：Keychain
- Windows：DPAPI 用户级加密
- Linux：Secret Service；如果不可用，则提示使用环境变量

配置文件只保存 `secret_ref`，不保存真实 Key。

## 本地配置路径

推荐用户配置文件：

```text
~/.config/blcaptain-opportunity-prd/model-pool.json
```

仓库里的 `templates/model-pool.providers.example.json` 只是示例，不保存真实密钥。

## 安全要求

- 不要把真实 API Key、token、cookie 写进 JSON、README、Prompt 或 Git 仓库。
- 配置文件只保存 `secret_ref`、环境变量名或 CLI 命令。
- 真实密钥优先放到系统安全凭据存储：macOS Keychain、Windows DPAPI、Linux Secret Service。
- 也可以使用 1Password、Bitwarden、本地私有 dotenv、环境变量或模型 CLI 登录态。
- 如果用户直接把 Key 粘贴给 Codex，必须立即写入本机安全凭据，不得写入 JSON、README、日志或报告。

## 验证

```bash
python3 scripts/setup_model_pool.py --doctor
python3 scripts/check_model_pool.py --config ~/.config/blcaptain-opportunity-prd/model-pool.json
```

通过健康检查后，才进入社区证据扫描、痛点分析、Gate 和 PRD 生成。
