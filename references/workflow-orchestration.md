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

- 工作流第一步必须是模型池 Bootstrap，并生成 `model-health.md/json`。
- `config_required` 时立即停止，只输出模型配置引导和 `workflow-summary`，不进入社区扫描、反向扫描、讨论、Gate 或 PRD。
- 默认不调用真实付费模型，只生成动态分工和讨论任务。
- 只有显式传入 `--run-discussion` 时，才调用健康检查通过的 CLI 或 OpenAI-compatible 模型。
- OpenAI-compatible 讨论输出必须有最终 `content`。仅返回 `reasoning_content` 时不写成有效讨论结论，而是提示关闭 thinking 或增大 `max_tokens`。
- `codex_builtin` 不由脚本重复调用，也不计入外部模型通过数；Codex 始终负责主持、综合、文件生成和校验。
- OpenAI-compatible 优先读取 `secret_ref` 指向的本机安全凭据，也兼容环境变量；不得把密钥写入输出文件。

## 输出目录

| 文件 | 内容 |
|---|---|
| `model-health.md/json` | 模型健康检查和置信模式 |
| `model-discussion.md/json` | 动态分工、讨论任务、可选模型输出 |
| `evidence-report.md/json/csv` | 正向社区证据墙 |
| `reverse-evidence-report.md/json/csv` | 反向证据墙 |
| `pain-clusters.md/json` | 痛点簇、证据集中度和候选最小切口 |
| `opportunity-assessment.md` | 机会评估报告 |
| `cut-to-go-assessment.md` | 原命题 Watch/Pivot 但存在集中痛点簇时的 Cut-to-Go 二次 Gate |
| `pivot-to-go-assessment.md` | 原切口 Pivot 时的新切口和二次 Gate |
| `commercial-opportunity-prd.md` | 仅 Go 时生成 |
| `workflow-summary.md/json` | 本轮结果摘要 |

## 决策规则

- `config_required`：ConfigRequired，立即停止，只输出配置引导。
- 意图严重缺失或有效证据少于 3 条：No-Go。
- 证据不足、可信度低或商业信号为 0：Watch。
- 正向证据成立但存在高风险反证：Pivot，必须尝试重新定义更小切口。
- Cut-to-Go：如果原命题过宽或初始结论是 Watch/Pivot，但评论证据已经集中到一个痛点簇，且该痛点簇有足够证据、平台覆盖和商业信号，则选择最小切口重新跑 G0 到 G8。
- Pivot-to-Go：如果反证可通过合规、成本、配置、ICP 或交付边界回应，则用同一批 evidence_id 和 reverse_id 重新跑 Gate。
- G0 到 G7 通过且 G8 可交接：Go，并生成商业化机会 PRD。

## 验收

Go 后必须运行：

```bash
python3 scripts/validate_opportunity_prd.py tests/runs/opportunity-workflow-go/commercial-opportunity-prd.md
```

如果校验失败，本轮不能标记为完成。
