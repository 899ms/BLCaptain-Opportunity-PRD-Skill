# 模型配置说明

## 目标

让用户在不理解 provider、routing、agent 等复杂概念的情况下，完成可用外部模型能力池配置。Codex 是主持者，不算外部模型。

## Codex 代配优先

默认先让用户用一句话告诉 Codex 要接入哪个模型，而不是让用户手动编辑 JSON。

用户可以这样说：

```text
帮我接入 DeepSeek。我有 API Key，环境变量名用 DEEPSEEK_API_KEY。
```

也可以这样说：

```text
帮我接入 Claude CLI。本机非交互命令是：claude -p
```

Codex 应该做：

1. 判断调用方式：OpenAI-compatible 还是 CLI。
2. 只追问最少必要信息：
   - OpenAI-compatible：`base_url`、`model`、`api_key_env`
   - CLI：本机非交互 `command`
3. 创建或更新本地模型配置文件；如果用户没有指定文件，优先建议 `my-model-pool.json`。
4. 明确提醒：真实 API Key、token、cookie 不得写入 JSON 或仓库。
5. 引导用户把密钥放到系统环境变量、macOS Keychain、1Password、Bitwarden、dotenv 本地私有文件或模型 CLI 登录态。
6. 运行 `scripts/check_model_pool.py --config <配置文件>`。
7. 用普通语言解释健康检查结果和下一步能做什么。

不要把配置过程包装成复杂的 provider、routing、agent 概念。用户只需要知道“我有什么模型、怎么调用、想让它负责什么”。

## 手动三步配置

### 第 1 步：添加模型

用户只需要输入自己拥有的外部模型名称或调用入口。

示例：

```text
Model A, Model B, Model C, Local Model
```

输出字段：

- 模型名称
- 用户备注
- 是否启用

### 第 2 步：填写调用方式

只展示用户能理解的调用方式：

- 环境变量
- OpenAI-compatible URL
- CLI 命令
- 暂不配置，仅记录模型名称

不要求用户理解供应商路由、成本模型、上下文长度或高级参数。高级能力可以后续扩展。

### 第 3 步：测试并选择用途

连接测试只检查是否能完成一次最小调用。通过后允许用户给模型打用途标签：

- 长文本
- 商业反方
- 结构化
- 外部趋势
- 代码实现
- 通用

如果用户不选择用途，主持 Agent 根据模型名称和实际表现做保守分配，并在输出中说明这是推断。

## 配置状态

| 状态 | 条件 | 下一步 |
|---|---|---|
| config_required | 无可用外部模型 | 只输出配置引导 |
| low_confidence | 只有 1 个外部模型通过健康检查 | 可继续低置信度初筛，但不声称多模型讨论 |
| standard | 2 到 3 个外部模型可用 | 主分析、反方、结构化角色可用 |
| heavy_discussion | 4 个及以上外部模型可用 | 可启用多视角讨论 |

## 首次触发引导

如果没有检测到可用外部模型，应输出：

```markdown
## 模型配置状态

当前未检测到可用外部模型。

Codex 可以主持流程，但为了完成多视角机会分析，建议至少配置 1 个外部模型；
如果要做商业反方和结构化审查，建议配置 2-3 个。

你可以选择以下任一方式：

1. 让 Codex 帮你配置，推荐
   - 直接说：帮我接入 DeepSeek / GLM / Claude / Gemini / Grok / 本地模型
   - 如果你有 API Key，只告诉 Codex 你想使用的环境变量名，不要发送真实 key
   - 如果你有 CLI，只提供本机非交互命令

2. DeepSeek / GLM / Gemini / Grok / 其他 OpenAI-compatible 模型
   - 需要：base_url、model 名称、API Key 环境变量名
   - 不要把真实 API Key 写进配置文件

3. Claude / Claude Code / 本地模型 CLI
   - 需要：一个本机可执行命令
   - 例如通过 CLI 返回一次文本响应即可

4. 暂不配置
   - 只用 Codex 主持做低置信度初筛
   - 不声称完成多模型讨论
```

然后让用户填最小表：

```markdown
| 模型 | 调用方式 | 你想让它负责什么 |
|---|---|---|
| DeepSeek | OpenAI-compatible / CLI / 不确定 | 通用 / 结构化 / 反方 |
| GLM | OpenAI-compatible / CLI / 不确定 | 长文本 / 结构化 / 代码 |
| Claude | CLI / 不确定 | 长文本 / 反方 / 通用 |
| Gemini | OpenAI-compatible / CLI / 不确定 | 外部趋势 / 多模态 / 通用 |
| Grok | OpenAI-compatible / CLI / 不确定 | 社交视角 / 外部趋势 / 反方 |
| 本地模型 | CLI / 不确定 | 通用 / 代码 / 成本敏感任务 |
```

## 配置示例

- 默认空模板：`templates/model-pool.example.json`
- 多供应商示例：`templates/model-pool.providers.example.json`

真实密钥不要写入配置文件。只填写环境变量名，例如 `DEEPSEEK_API_KEY`、`GLM_API_KEY`、`GEMINI_API_KEY`、`GROK_API_KEY`。真实密钥建议保存在系统环境变量、macOS Keychain、1Password、Bitwarden、dotenv 本地私有文件或模型 CLI 自己的登录态中。

## 输出要求

使用 `templates/model-config-status.md`。必须写明：

- 已配置外部模型数
- 通过健康检查的外部模型数
- Codex 主持状态
- 置信模式
- 每个模型的用途标签
- 降级说明

## 硬约束

- 无可用外部模型时不得声称完成多模型讨论。
- 只有一个外部模型时不得声称完成多模型讨论。
- 不得把具体模型名称写死为固定职责。
