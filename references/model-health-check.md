# P1 模型健康检查

## 目标

让用户配置自己的模型能力池，但不把密钥写进仓库或报告。

## 配置格式

优先让 Codex 帮用户生成或更新本地模型配置文件。用户只需要说“帮我接入 DeepSeek”或“帮我接入 Claude CLI，命令是 `claude -p`”。手动配置时使用 JSON：默认 `templates/model-pool.example.json` 是空模型池，新用户可参考 `templates/model-pool.providers.example.json`。

支持三种方法：

| method | 用途 | 是否需要密钥 |
|---|---|---|
| cli | 本地模型、第三方 CLI、包装脚本 | 由用户本地命令自行处理 |
| openai_compatible | OpenAI-compatible `/chat/completions` API | 优先写 `secret_ref`，不写真实密钥 |
| codex_builtin | Codex 主持说明，不计入外部模型 | 不需要 |

## 命令

```bash
python3 scripts/setup_model_pool.py --doctor
python3 scripts/setup_model_pool.py --init
python3 scripts/setup_model_pool.py connect deepseek --store auto --prompt-key
python3 scripts/check_model_pool.py --config templates/model-pool.example.json
python3 scripts/check_model_pool.py --config templates/model-pool.providers.example.json
```

可输出报告：

```bash
python3 scripts/check_model_pool.py \
  --config templates/model-pool.example.json \
  --output tests/runs/model-health-report.md
```

也可输出结构化健康检查：

```bash
python3 scripts/check_model_pool.py \
  --config templates/model-pool.example.json \
  --output tests/runs/model-health-report.md \
  --json-output tests/runs/model-health-report.json
```

## 输出模式

- `config_required`：无可用外部模型，只输出配置引导。
- `low_confidence`：只有 1 个外部模型可用，可以初筛但不能声称多模型讨论。
- `standard`：2 到 3 个外部模型可用，可做主分析、反方、结构化。
- `heavy_discussion`：4 个以上外部模型可用，可做多视角讨论。

## 安全规则

- 配置文件只保存 `secret_ref`、环境变量名或 CLI 命令，不保存真实密钥。
- `--store auto` 默认选择系统安全凭据：macOS Keychain、Windows DPAPI、Linux Secret Service。
- 如果系统安全凭据不可用，则提示使用环境变量、1Password、Bitwarden、dotenv 本地私有文件或模型 CLI 自己的登录态。
- 报告不得打印完整密钥。
- 占位 base_url、model 或 command 输出 `missing_config`，引导用户补配置，不执行占位命令。
- 缺少密钥时输出 `missing_secret`，并提示使用 `setup_model_pool.py connect <model> --store auto --prompt-key`，不得伪装成功。
- CLI 命令由用户本地环境负责权限和密钥管理。
- OpenAI-compatible 健康通过不等于 HTTP 200。必须满足：HTTP 200、响应 JSON 可解析，并且 `choices[0].message.content` 非空。
- 仅返回 `reasoning_content` 不计为通过，因为它不能作为多模型讨论的最终回答。此时提示用户关闭 thinking 或增大 `max_tokens`。
- 思考型模型做短审查、机会判断和结构审查时，默认关闭 thinking 并设置足够的 `max_tokens`；只有长程 coding 或明确需要深度推理时才显式开启 thinking。

## 候选发现

健康检查会展示两类可接入候选：

- OpenAI-compatible：DeepSeek、GLM、Gemini、Grok 等，只提示建议环境变量名和用途标签。
- 本机 CLI：Claude CLI、Gemini CLI、Ollama 本地模型等，只检查命令是否在 PATH 中。

候选发现只用于引导用户配置，不会计入外部模型通过数。只有用户把模型写入自己的模型池 JSON，并通过健康检查后，才允许参与动态分工和 `--run-discussion`。

## 工作流硬停止

`run_opportunity_workflow.py` 必须先生成 `model-health.md/json`。当模式是 `config_required` 时，本轮只输出模型接入引导和 `workflow-summary`，不得继续生成平台路由、证据墙、反向证据墙、模型讨论、Gate 评估或 PRD。
