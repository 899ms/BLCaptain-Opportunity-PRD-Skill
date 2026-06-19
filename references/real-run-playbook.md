# P4 真实运行 Playbook

## 目标

让用户在不泄露密钥、不登录私密社区的前提下，用真实公开 URL、本地导出评论和自己的模型配置跑一次接近生产的机会挖掘。

## 文件

| 文件 | 用途 |
|---|---|
| `templates/real-run-case.example.json` | 真实运行 case 配置模板 |
| `templates/model-pool.real.example.json` | 真实模型配置模板，只保存环境变量名 |
| `templates/model-pool.providers.example.json` | DeepSeek、GLM、Claude CLI、Gemini、Grok、本地模型配置示例 |
| `scripts/prepare_real_run.py` | 审计 URL、生成快照、检查模型、可选运行 P3 工作流 |

## 三步运行

1. 复制并改 case 配置：

```bash
cp templates/real-run-case.example.json tests/runs/my-real-case.json
```

2. 参考 `templates/model-pool.providers.example.json` 配置模型。真实密钥只放到环境变量、macOS Keychain、1Password、Bitwarden、dotenv 本地私有文件或模型 CLI 登录态中，不写进 JSON：

```bash
export DEEPSEEK_API_KEY="..."
export GLM_API_KEY="..."
export GEMINI_API_KEY="..."
export GROK_API_KEY="..."
```

3. 准备真实运行并衔接工作流：

```bash
python3 scripts/prepare_real_run.py \
  --case-config tests/runs/my-real-case.json \
  --output-dir tests/runs/my-real-run \
  --run-workflow \
  --run-discussion
```

## URL 和来源规则

- `url`：只支持公开 HTTP/HTTPS 页面，会快照到本地 Markdown 后再扫描。
- `file`：适合用户从社区、客服系统、表格或浏览器手动导出的样本。
- `directory`：适合一次放多个导出文件。
- 默认阻止 localhost、内网和私有 IP URL；只有本地测试时才加 `--allow-local`。

## 输出

准备阶段输出：

- `real-run-audit.md/json`
- `model-health.md/json`
- `sources-positive.generated.json`
- `sources-reverse.generated.json`
- `raw/positive/*.md`
- `raw/reverse/*.md`

如果加 `--run-workflow`，还会输出：

- `workflow/model-discussion.md/json`
- `workflow/evidence-report.md/json/csv`
- `workflow/reverse-evidence-report.md/json/csv`
- `workflow/opportunity-assessment.md`
- `workflow/commercial-opportunity-prd.md`，仅 Go 时生成
- `workflow/workflow-summary.md/json`

## 停止线

- 全部 URL 失败或被阻止：不要进入 Go，先补样本。
- 外部模型全为 `missing_config`、`missing_secret` 或 `failed`：只做配置引导，不声称完成多模型讨论；Codex 只负责主持，不计入外部模型通过数。
- 公开 URL 中没有用户原话：只作趋势背景，不作需求证据。
- 私密群、登录后台、付费 API：不自动抓取，只接受用户授权后导出的样本。
