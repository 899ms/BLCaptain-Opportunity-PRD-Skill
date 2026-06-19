#!/usr/bin/env python3
"""Validate opportunity assessment reports and commercial opportunity PRDs."""

from __future__ import annotations

import re
import sys
from pathlib import Path


DECISIONS = ("Go", "Watch", "Pivot", "No-Go")

GO_BUSINESS_MARKERS = [
    "用户原话",
    "行为信号",
    "商业信号",
    "Gate",
    "7 天",
    "P0",
    "evidence_id",
    "验收剧本",
]

GO_ENGINEERING_MARKERS = [
    "工程实施方案",
    "系统架构",
    "数据流",
    "技术选型",
    "AI 风险标注方案",
    "字段字典",
    "API 契约",
    "错误码",
    "权限",
    "隐私",
    "删除策略",
    "审计日志",
    "非功能需求",
    "异常流程",
    "测试方案",
    "部署运维",
    "监控",
    "埋点",
    "开发任务拆分",
    "DoD",
    "置信度",
    "成本上限",
]


def find_decision(text: str) -> str | None:
    patterns = [
        r"结论\s*\|\s*(Go|Watch|Pivot|No-Go)\s*\|",
        r"决策\s*[:：]\s*(Go|Watch|Pivot|No-Go)",
        r"结论\s*[:：]\s*(Go|Watch|Pivot|No-Go)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def count_unique(pattern: str, text: str) -> int:
    return len(set(re.findall(pattern, text)))


def validate_non_go(text: str, decision: str, errors: list[str]) -> None:
    if decision == "Go":
        return

    if re.search(r"^#\s*商业化机会(?: \+ 工程实施)? PRD|^##\s*0\.\s*商业速读卡", text, flags=re.M):
        errors.append(f"{decision} 文档不得生成商业化机会 PRD 正文")

    required_markers = ["机会评估报告", "Gate", "不生成商业化机会 PRD"]
    for marker in required_markers:
        if marker not in text:
            errors.append(f"{decision} 文档缺少 {marker}")

    if not any(term in text for term in ["缺少用户原话", "证据不足", "商业信号不足", "停止"]):
        errors.append(f"{decision} 文档必须说明停止或补证原因")


def validate_go(text: str, errors: list[str]) -> None:
    evidence_count = count_unique(r"\bE-\d{3}\b", text)
    reverse_count = count_unique(r"\bR-\d{3}\b", text)
    date_count = count_unique(r"\b20\d{2}-\d{2}-\d{2}\b", text)
    source_count = count_unique(r"(?:https?://[^\s|)]+|tests/(?:fixtures|runs)/[^\s|)]+)", text)

    if "商业化机会" not in text or "PRD" not in text:
        errors.append("Go 文档必须包含商业化机会 PRD")
    if "工程实施 PRD" not in text and "工程实施方案" not in text:
        errors.append("Go 文档必须升级为工程实施级 PRD，不能只写机会说明")
    if evidence_count < 5:
        errors.append(f"Go 文档至少需要 5 条 evidence_id，当前 {evidence_count}")
    if reverse_count < 3:
        errors.append(f"Go 文档至少需要 3 条 reverse_id，当前 {reverse_count}")
    if date_count < 5:
        errors.append(f"Go 文档至少需要 5 个日期，当前 {date_count}")
    if source_count < 5:
        errors.append(f"Go 文档至少需要 5 个 URL 或可追溯来源，当前 {source_count}")

    for marker in GO_BUSINESS_MARKERS:
        if marker not in text:
            errors.append(f"Go 文档缺少 {marker}")

    for marker in GO_ENGINEERING_MARKERS:
        if marker not in text:
            errors.append(f"Go 文档缺少工程实施字段：{marker}")

    if not re.search(r"P0[\s\S]*E-\d{3}", text):
        errors.append("P0 功能必须绑定 evidence_id")

    if len(re.findall(r"\| /api/", text)) < 3:
        errors.append("Go 文档至少需要 3 个 API 契约")

    if len(set(re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b", text))) < 6:
        errors.append("Go 文档至少需要 6 个明确错误码或配置码")

    if len(re.findall(r"\| (?:ImportBatch|Conversation|RiskFinding|WeeklyReport|AuditLog) \|", text)) < 5:
        errors.append("Go 文档字段字典至少需要覆盖 ImportBatch、Conversation、RiskFinding、WeeklyReport、AuditLog")

    acceptance_count = len(re.findall(r"验收剧本\s*\d|^\d+\.\s*", text, flags=re.M))
    if acceptance_count < 3:
        errors.append(f"Go 文档至少需要 3 条验收剧本，当前 {acceptance_count}")

    if not any(term in text for term in ["付费", "成本节省", "弃用竞品", "购买意图"]):
        errors.append("Go 文档必须包含付费、成本节省、弃用竞品或购买意图之一")


def lint_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    decision = find_decision(text)
    if decision not in DECISIONS:
        errors.append("缺少决策结论：Go / Watch / Pivot / No-Go")
        return errors

    if decision == "Go":
        validate_go(text, errors)
    else:
        validate_non_go(text, decision, errors)

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python3 scripts/validate_opportunity_prd.py <report.md>", file=sys.stderr)
        return 2

    path = Path(argv[1])
    if not path.exists():
        print(f"文件不存在：{path}", file=sys.stderr)
        return 2

    errors = lint_file(path)
    if errors:
        print(f"validate_opportunity_prd failed: {path}")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"validate_opportunity_prd passed: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
