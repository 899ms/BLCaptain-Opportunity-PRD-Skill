# P2 社区证据扫描

## 目标

从公开 URL、本地样本或样本目录中抽取候选评论证据，生成可进入证据墙的 Markdown、JSON 和 CSV 报告。

## 来源格式

使用 JSON，参考 `templates/community-sources.example.json`。

支持三类来源：

| type | 用途 |
|---|---|
| file | 本地 Markdown、TXT、HTML 样本 |
| url | 公开网页 URL |
| directory | 本地目录，批量读取 `.md`、`.txt`、`.html`、`.htm` |

P2 不支持登录态、私密群聊、付费 API 或绕过访问限制。需要这些来源时，让用户导出样本或提供授权 API。

## 命令

```bash
python3 scripts/scan_community_evidence.py \
  --idea "AI 客服质检工具" \
  --sources templates/community-sources.example.json \
  --output tests/runs/community-evidence-report.md
```

结构化导出：

```bash
python3 scripts/scan_community_evidence.py \
  --idea "AI 客服质检工具" \
  --sources tests/fixtures/community-batch-sources-local.json \
  --output tests/runs/community-evidence-batch.md \
  --json-output tests/runs/community-evidence-batch.json \
  --csv-output tests/runs/community-evidence-batch.csv
```

反向证据扫描：

```bash
python3 scripts/scan_reverse_evidence.py \
  --idea "AI 客服质检工具" \
  --sources tests/fixtures/reverse-sources-local.json \
  --output tests/runs/reverse-evidence-report.md \
  --json-output tests/runs/reverse-evidence-report.json \
  --csv-output tests/runs/reverse-evidence-report.csv
```

## 抽取字段

正向证据脚本输出：

- evidence_id
- 平台
- 日期
- URL 或本地路径
- 用户原话
- 行为信号
- 商业信号
- 等级

反向证据脚本输出：

- reverse_id
- 来源
- 日期
- URL 或本地路径
- 反向证据
- 影响
- 回应
- 结论
- 风险等级
- 标签

## 判断规则

- 行为信号来自手动、截图、表格、每天、半天、manual、spreadsheet 等关键词。
- 商业信号来自付费、收费、太贵、预算、成本、订阅、expensive、paying 等关键词。
- 正向脚本只生成正向证据候选；Go 前仍必须补反向证据。
- 扫描结果为 `Go-candidate` 时，也不能直接生成商业化机会 PRD。
- 反向脚本发现 `Pivot-required` 时，先调整 ICP、定价、数据方案或 P0 范围。

## 降级

- 有效证据少于 3 条：No-Go。
- 有证据但平台不足或商业信号不足：Watch。
- 有 5 条以上证据且有商业信号：Go-candidate，进入反向证据审查。
- 反向证据无法回应：Pivot 或 No-Go。
