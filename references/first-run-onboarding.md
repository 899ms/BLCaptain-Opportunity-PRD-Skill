# 首次运行引导

## 目标

让新用户安装后先完成模型 Agent 配置，再进入机会挖掘。这个步骤不是可选评审，而是本 skill 的入口。

## 触发条件

出现以下任一情况时，先输出首次运行引导：

- 没有传入 `--model-config`。
- 环境变量 `BLCAPTAIN_MODEL_POOL` 未设置。
- `~/.config/blcaptain-opportunity-prd/model-pool.json` 不存在。
- 模型池存在，但没有外部模型通过健康检查。

## 输出内容

必须展示：

1. Codex 是主持者，不计入外部模型。
2. 支持的模型 Agent 类型：OpenAI-compatible、CLI、本地模型、代码/原型 Agent。
3. 用户可以直接说“帮我接入某个模型”。
4. 推荐本地配置路径：`~/.config/blcaptain-opportunity-prd/model-pool.json`。
5. 密钥安全：只写环境变量名，不写真实 key。
6. 健康检查命令。
7. 配置完成前不进入机会分析。

## 推荐命令

```bash
python3 scripts/setup_model_pool.py --doctor
python3 scripts/setup_model_pool.py --init
python3 scripts/check_model_pool.py --config ~/.config/blcaptain-opportunity-prd/model-pool.json
```

## Codex 代配流程

当用户说“帮我接入 DeepSeek / GLM / Claude CLI / Gemini / Grok / Ollama / 本地模型”时：

1. 判断接入方式：OpenAI-compatible 或 CLI。
2. 只追问最少必要信息。
3. 生成或更新用户本地模型池配置。
4. 提醒真实密钥放在环境变量、Keychain、密码管理器、本地私有 dotenv 或 CLI 登录态。
5. 运行健康检查。
6. 根据通过模型数量说明可进入的工作模式。

## 停止线

`config_required` 时，本轮只输出模型配置状态、候选 Agent 和下一步，不输出证据墙、Gate、机会评估或 PRD。
