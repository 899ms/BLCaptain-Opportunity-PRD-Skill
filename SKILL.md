---
name: BLCaptain Opportunity PRD Skill
description: |
  从社区评论证据挖掘产品机会并生成商业化 PRD 的 Codex skill。Use when the user wants to turn a product idea,赛道,评论样本,社区帖子,机会卡,痛点线索,竞品评价,或用户反馈 into an evidence-backed opportunity assessment, No-Go/Watch/Pivot/Go decision, 7-day validation plan, or commercial opportunity PRD. This skill requires model configuration status first, dynamic multi-model role assignment when available, community evidence, reverse evidence, business Gate checks, and Codex-led final synthesis.
---

# BLCaptain Opportunity PRD Skill

把一句产品想法或一组社区评论，转成可追溯的机会评估报告；只有 Gate 通过时，才生成商业化机会 + 工程实施 PRD。

## 运行原则

- 始终中文优先输出，除非用户明确要求英文。
- 始终先确认模型能力池状态：无可用外部模型时只输出配置引导；一个外部模型时标注单模型低置信度；两个及以上外部模型时动态分工。
- 始终由 Codex 主持：Codex 负责拆任务、分配模型视角、处理冲突、写文件、跑校验和交接实现。
- Codex 主持能力不等于外部模型能力；`codex_builtin` 只用于说明主持可用，不计入外部模型通过数。
- 当用户说“接入某个模型”“我有某个 API Key”“我有某个 CLI 命令”时，优先用引导式配置：询问最少必要信息，帮用户生成或更新本地模型配置文件，提醒密钥不要写入 JSON，然后运行健康检查；不要默认要求用户手动编辑配置文件。
- 不硬编码任何固定模型职责；根据用户实际配置和能力标签分配任务。
- 不固定社区平台；根据用户、场景、行业、竞品和问题类型动态选择平台。
- 不把趋势、公告、观点文章、营销软文当作已验证需求。
- 没有用户原话、URL、日期、手动行为、商业信号和反向证据时，不生成“已验证需求”型 PRD。
- 默认终点是机会评估报告；只有判断为 Go 时才生成商业化机会 + 工程实施 PRD。
- Go 后最终 PRD 必须能指导研发实施，包含系统架构、数据流、技术选型、字段字典、API 契约、安全隐私、异常流程、测试、部署运维、埋点和开发任务 DoD。

## 快速流程

1. 读取模型配置状态。需要配置时，使用 `references/model-config-guide.md`；需要真实健康检查时运行 `scripts/check_model_pool.py`，规则见 `references/model-health-check.md`。
2. 如果用户要接入模型，先按 `references/model-config-guide.md` 的“Codex 代配优先”流程收集模型名、调用方式、环境变量名或 CLI 命令，更新本地配置并跑健康检查。
3. 根据可用外部模型生成动态角色表。使用 `references/model-assignment.md`。
4. 把用户输入拆成意图卡：目标用户、场景、核心动作、替代方案、商业假设、未知项。
5. 做平台路由和关键词计划。使用 `references/platform-routing.md` 和 `references/community-platform-catalog.md`；需要扫描公开 URL、本地样本或目录时运行 `scripts/scan_community_evidence.py`，规则见 `references/community-evidence-scan.md`。
6. 建立证据墙和反向证据墙。使用 `references/evidence-rules.md`；需要扫描反向证据时运行 `scripts/scan_reverse_evidence.py`。
7. 选择最小方法论组合。使用 `references/methodology-router.md`。
8. 按 G0 到 G8 运行 Gate。使用 `references/workflow-gates.md`。
9. 输出机会评估报告；只有 Go 时继续输出商业化机会 + 工程实施 PRD。使用 `references/commercial-prd-contract.md`。
10. 需要真实 URL、用户导出样本或真实模型配置演练时，运行 `scripts/prepare_real_run.py`，规则见 `references/real-run-playbook.md`。
11. 需要端到端执行时，运行 `scripts/run_opportunity_workflow.py`，规则见 `references/workflow-orchestration.md`。
12. 生成或检查文件时，运行 `scripts/quick_validate.py` 或 `scripts/validate_opportunity_prd.py`。

## 八步工作法

每次执行都遵循：

```text
调研 -> 分析 -> 计划 -> 开发 -> 验证 -> 测试 -> 审计验收 -> 总结
```

调研贯穿每一步。任何一步证据不足、模型不可用、Gate 不通过或校验失败，都回到调研补证，而不是编造结论。

详细规则见 `references/eight-step-workflow.md`。

## 输出顺序

按需要输出以下资产，不要跳过 Gate：

1. 模型配置状态
2. 动态模型分工
3. 意图卡
4. 平台路由和搜索式
5. 评论证据墙
6. 反向证据墙
7. 方法论选择和结论
8. Gate 结果
9. 机会评估报告
10. 7 天关键假设实验
11. 商业化机会 + 工程实施 PRD，仅限 Go

## 模板

- `templates/model-config-status.md`
- `templates/intent-card.md`
- `templates/evidence-pack.md`
- `templates/opportunity-assessment-report.md`
- `templates/commercial-opportunity-prd.md`

## 校验

结构校验：

```bash
python3 scripts/quick_validate.py
```

模型健康检查：

```bash
python3 scripts/check_model_pool.py --config templates/model-pool.example.json
```

新用户模型配置示例：

```bash
python3 scripts/check_model_pool.py --config templates/model-pool.providers.example.json
```

社区证据扫描：

```bash
python3 scripts/scan_community_evidence.py --idea "AI 客服质检工具" --sources templates/community-sources.example.json
```

结构化导出：

```bash
python3 scripts/scan_community_evidence.py --idea "AI 客服质检工具" --sources templates/community-sources.example.json --json-output evidence.json --csv-output evidence.csv
```

反向证据扫描：

```bash
python3 scripts/scan_reverse_evidence.py --idea "AI 客服质检工具" --sources templates/community-sources.example.json
```

端到端工作流：

```bash
python3 scripts/run_opportunity_workflow.py --idea "AI 客服质检工具" --model-config templates/model-pool.example.json --sources templates/community-sources.example.json --output-dir tests/runs/opportunity-workflow
```

真实运行准备：

```bash
python3 scripts/prepare_real_run.py --case-config templates/real-run-case.example.json --output-dir tests/runs/real-run-prep
```

机会评估或商业化 + 工程实施 PRD 校验：

```bash
python3 scripts/validate_opportunity_prd.py path/to/report.md
```

## 停止线

- 无可用外部模型：只输出配置引导；Codex 只主持低置信度初筛，不声称完成多模型讨论。
- 有效证据少于 3 条：输出证据不足报告。
- 没有商业信号：输出 Watch，不生成商业化机会 + 工程实施 PRD。
- 反向证据无法回应：输出 Pivot 或 No-Go。
- 任一 P0 功能没有 evidence_id：修复 PRD 或删除该功能。
