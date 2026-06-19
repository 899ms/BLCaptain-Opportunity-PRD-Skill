# P3 端到端工作流编排

## 目标

把模型配置、社区证据、反向证据、动态模型分工、Gate、机会评估报告和商业化机会 PRD 串成一个可运行闭环。

## 命令

```bash
python3 scripts/run_opportunity_workflow.py \
  --idea "AI 客服质检工具" \
  --model-config tests/fixtures/model-pool-cli.json \
  --sources tests/fixtures/community-batch-sources-local.json \
  --reverse-sources tests/fixtures/reverse-sources-go-local.json \
  --output-dir tests/runs/opportunity-workflow-go \
  --run-discussion
```

## 默认安全策略

- 默认不调用真实付费模型，只生成动态分工和讨论任务。
- 只有显式传入 `--run-discussion` 时，才调用健康检查通过的 CLI 或 OpenAI-compatible 模型。
- `codex_builtin` 不由脚本重复调用，Codex 始终负责主持、综合、文件生成和校验。
- OpenAI-compatible 只读取环境变量中的 API Key，不把密钥写入输出文件。

## 输出目录

| 文件 | 内容 |
|---|---|
| `model-health.md/json` | 模型健康检查和置信模式 |
| `model-discussion.md/json` | 动态分工、讨论任务、可选模型输出 |
| `evidence-report.md/json/csv` | 正向社区证据墙 |
| `reverse-evidence-report.md/json/csv` | 反向证据墙 |
| `opportunity-assessment.md` | 机会评估报告 |
| `commercial-opportunity-prd.md` | 仅 Go 时生成 |
| `workflow-summary.md/json` | 本轮结果摘要 |

## 决策规则

- `config_required`、意图严重缺失或有效证据少于 3 条：No-Go。
- 证据不足、可信度低或商业信号为 0：Watch。
- 正向证据成立但存在高风险反证：Pivot。
- G0 到 G7 通过且 G8 可交接：Go，并生成商业化机会 PRD。

## 验收

Go 后必须运行：

```bash
python3 scripts/validate_opportunity_prd.py tests/runs/opportunity-workflow-go/commercial-opportunity-prd.md
```

如果校验失败，本轮不能标记为完成。
