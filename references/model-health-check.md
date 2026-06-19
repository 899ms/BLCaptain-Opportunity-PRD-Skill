# P1 模型健康检查

## 目标

让用户配置自己的模型能力池，但不把密钥写进仓库或报告。

## 配置格式

使用 JSON，参考 `templates/model-pool.example.json`。

支持三种方法：

| method | 用途 | 是否需要密钥 |
|---|---|---|
| cli | 本地模型、第三方 CLI、包装脚本 | 由用户本地命令自行处理 |
| openai_compatible | OpenAI-compatible `/chat/completions` API | 只写环境变量名，不写密钥 |
| codex_builtin | 当前 Codex 主持能力 | 不需要 |

## 命令

```bash
python3 scripts/check_model_pool.py --config templates/model-pool.example.json
```

可输出报告：

```bash
python3 scripts/check_model_pool.py \
  --config templates/model-pool.example.json \
  --output tests/runs/model-health-report.md
```

## 输出模式

- `config_required`：无可用模型，只输出配置引导。
- `low_confidence`：只有 1 个可用模型，可以初筛但不能声称多模型讨论。
- `standard`：2 到 3 个可用模型，可做主分析、反方、结构化。
- `heavy_discussion`：4 个以上可用模型，可做多视角讨论。

## 安全规则

- 配置文件只保存环境变量名，例如 `OPENAI_API_KEY`，不保存真实密钥。
- 报告不得打印完整密钥。
- 缺少密钥时输出 `missing_secret`，不得伪装成功。
- CLI 命令由用户本地环境负责权限和密钥管理。
