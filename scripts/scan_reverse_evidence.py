#!/usr/bin/env python3
"""Scan public URLs or local files for reverse evidence before Go decisions."""

from __future__ import annotations

import argparse
import csv
import html.parser
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ROOT / "templates" / "community-sources.example.json"
DATE_PATTERN = re.compile(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b")

REVERSE_RULES = [
    {
        "label": "免费替代",
        "keywords": ["免费", "免费版", "表格够用", "free", "free tier", "free alternative", "spreadsheet is enough"],
        "impact": "可能压低付费意愿，需要证明节省时间或结果质量显著更好。",
        "response": "把付费点限定到自动化、团队协作、可追溯报告或合规留痕。",
        "risk": "medium",
    },
    {
        "label": "内置方案",
        "keywords": ["内置", "系统自带", "already built in", "built-in", "native feature", "included"],
        "impact": "竞品或现有系统已覆盖基础场景，差异化空间变小。",
        "response": "避开基础功能，寻找跨工具整合、行业模板或更低实施成本。",
        "risk": "medium",
    },
    {
        "label": "预算不足",
        "keywords": ["没预算", "没有预算", "预算不够", "too expensive", "no budget", "can't afford", "cannot afford"],
        "impact": "目标客群可能有痛点但没有购买能力。",
        "response": "重估 ICP、定价层级和可触达的付费决策人。",
        "risk": "high",
    },
    {
        "label": "隐私合规",
        "keywords": ["隐私", "合规", "数据安全", "不能上传", "privacy", "compliance", "security", "cannot upload"],
        "impact": "数据访问可能阻断产品落地或显著增加交付成本。",
        "response": "提前验证本地部署、脱敏、权限审计和数据保留策略。",
        "risk": "high",
    },
    {
        "label": "复杂度过高",
        "keywords": ["太复杂", "配置太麻烦", "setup is too heavy", "too complex", "hard to configure"],
        "impact": "用户可能拒绝采用，尤其是小团队和低频场景。",
        "response": "把 P0 收敛到一个默认报告或一个最小动作，不做重配置平台。",
        "risk": "medium",
    },
    {
        "label": "低频一次性",
        "keywords": ["偶尔", "一次性", "不常用", "rarely", "one-off", "not often"],
        "impact": "使用频次不足，订阅商业模式可能不成立。",
        "response": "验证高频细分场景，或改为项目制、按量、模板包。",
        "risk": "medium",
    },
]


class TextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if cleaned:
            self.parts.append(cleaned)

    def text(self) -> str:
        return "\n".join(self.parts)


@dataclass
class Source:
    id: str
    platform: str
    url: str
    source_type: str


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_source(source: Source, timeout: int) -> str:
    if source.source_type == "file":
        path = Path(source.url)
        if not path.is_absolute():
            path = ROOT / path
        return path.read_text(encoding="utf-8")

    if source.source_type == "directory":
        path = Path(source.url)
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_dir():
            raise ValueError(f"directory source not found: {path}")
        parts: list[str] = []
        for child in sorted(path.rglob("*")):
            if child.suffix.lower() not in {".md", ".txt", ".html", ".htm"}:
                continue
            parts.append(child.read_text(encoding="utf-8"))
        return "\n\n".join(parts)

    if source.source_type == "url":
        request = urllib.request.Request(
            source.url,
            headers={"User-Agent": "opportunity-to-commercial-prd/1.0"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(1_000_000)
            content_type = response.headers.get("Content-Type", "")
        text = raw.decode("utf-8", errors="replace")
        if "html" in content_type or "<html" in text[:500].lower():
            parser = TextExtractor()
            parser.feed(text)
            return parser.text()
        return text

    raise ValueError(f"unsupported source_type: {source.source_type}")


def split_blocks(text: str) -> list[str]:
    blocks = re.split(r"\n\s*\n|(?=^\s*[-*]\s)", text, flags=re.M)
    return [" ".join(block.strip().split()) for block in blocks if len(block.strip()) >= 20]


def extract_date(text: str) -> str:
    match = DATE_PATTERN.search(text)
    return match.group(0).replace("/", "-") if match else "未知"


def extract_platform(text: str, fallback: str) -> str:
    match = re.search(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\s+([^:：]{2,40})[:：]", text)
    if not match:
        return fallback
    platform = re.sub(r"^(?:[-*]\s*)", "", match.group(1).strip())
    return platform or fallback


def compact_quote(text: str) -> str:
    text = re.sub(r"^\s*[-*]\s*", "", text).strip()
    return text[:180] + ("..." if len(text) > 180 else "")


def matched_rules(text: str) -> list[dict[str, Any]]:
    lowered = text.lower()
    results = []
    for rule in REVERSE_RULES:
        if any(keyword.lower() in lowered for keyword in rule["keywords"]):
            results.append(rule)
    return results


def scan_sources(sources: list[Source], timeout: int) -> list[dict[str, str]]:
    reverse_items: list[dict[str, str]] = []
    seen_quotes: set[str] = set()
    for source in sources:
        text = read_source(source, timeout)
        for block in split_blocks(text):
            rules = matched_rules(block)
            if not rules:
                continue
            normalized_quote = compact_quote(block)
            if normalized_quote in seen_quotes:
                continue
            seen_quotes.add(normalized_quote)
            risk = "high" if any(rule["risk"] == "high" for rule in rules) else "medium"
            reverse_items.append(
                {
                    "source": extract_platform(block, source.platform),
                    "date": extract_date(block),
                    "url": source.url,
                    "reverse_evidence": normalized_quote,
                    "impact": "；".join(rule["impact"] for rule in rules),
                    "response": "；".join(rule["response"] for rule in rules),
                    "conclusion": "阻断项" if risk == "high" else "压力测试项",
                    "risk": risk,
                    "labels": "、".join(rule["label"] for rule in rules),
                }
            )
    for index, item in enumerate(reverse_items, start=1):
        item["reverse_id"] = f"R-{index:03d}"
    return reverse_items


def reverse_stats(reverse_items: list[dict[str, str]]) -> dict[str, Any]:
    high_risk_count = len([item for item in reverse_items if item["risk"] == "high"])
    decision = "Clear-to-next-gate"
    reason = "未发现明显反向证据，但仍需人工复核样本覆盖。"
    if high_risk_count >= 2:
        decision = "Pivot-required"
        reason = "发现多个高风险反向证据，Go 前必须调整 ICP、方案或交付边界。"
    elif reverse_items:
        decision = "Pressure-test"
        reason = "存在反向证据，需要逐条回应后再进入商业化 PRD。"
    return {
        "decision": decision,
        "reason": reason,
        "reverse_count": len(reverse_items),
        "high_risk_count": high_risk_count,
        "labels": sorted({label for item in reverse_items for label in item["labels"].split("、") if label}),
    }


def to_payload(idea: str, sources: list[Source], reverse_items: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "version": "1.0",
        "idea": idea,
        "stats": reverse_stats(reverse_items),
        "sources": [source.__dict__ for source in sources],
        "reverse_evidence": reverse_items,
    }


def to_markdown(idea: str, sources: list[Source], reverse_items: list[dict[str, str]]) -> str:
    stats = reverse_stats(reverse_items)
    lines = [
        "# 反向证据扫描报告",
        "",
        f"- 想法：{idea}",
        f"- 决策：{stats['decision']}",
        f"- 理由：{stats['reason']}",
        "",
        "## 来源",
        "",
        "| source_id | 平台 | 类型 | URL/路径 |",
        "|---|---|---|---|",
    ]
    for source in sources:
        lines.append(f"| {source.id} | {source.platform} | {source.source_type} | {source.url} |")

    lines.extend(
        [
            "",
            "## 反向证据墙",
            "",
            "| reverse_id | 来源 | 日期 | URL | 反向证据 | 影响 | 回应 | 结论 |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in reverse_items:
        lines.append(
            "| {reverse_id} | {source} | {date} | {url} | {reverse_evidence} | {impact} | {response} | {conclusion} |".format(
                **item
            )
        )

    lines.extend(
        [
            "",
            "## 样本统计",
            "",
            "| 指标 | 数值 |",
            "|---|---:|",
            f"| 来源数 | {len(sources)} |",
            f"| 反向证据数 | {stats['reverse_count']} |",
            f"| 高风险反向证据数 | {stats['high_risk_count']} |",
            f"| 反向标签数 | {len(stats['labels'])} |",
            "",
            "## 下一步",
            "",
            "- Pressure-test 时逐条写回应，不得直接生成商业化机会 PRD。",
            "- Pivot-required 时先调整 ICP、定价、数据方案或 P0 范围，再回到证据扫描。",
        ]
    )
    return "\n".join(lines)


def parse_sources(config_path: Path) -> list[Source]:
    config = load_json(config_path)
    sources = []
    for raw in config.get("sources", []):
        sources.append(
            Source(
                id=raw.get("id", f"S{len(sources)+1}"),
                platform=raw.get("platform", "unknown"),
                url=raw["url"],
                source_type=raw.get("type", "file"),
            )
        )
    return sources


def write_json(path: str, payload: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Scan reverse evidence from public URLs, local files, or directories.")
    parser.add_argument("--idea", required=True, help="Product idea or opportunity hypothesis.")
    parser.add_argument("--sources", default=str(DEFAULT_SOURCES), help="JSON file with sources.")
    parser.add_argument("--output", help="Optional Markdown report path.")
    parser.add_argument("--json-output", help="Optional structured JSON output path.")
    parser.add_argument("--csv-output", help="Optional reverse-evidence CSV output path.")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args(argv)

    sources = parse_sources(Path(args.sources))
    reverse_items = scan_sources(sources, args.timeout)
    markdown = to_markdown(args.idea, sources, reverse_items)
    payload = to_payload(args.idea, sources, reverse_items)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
    if args.json_output:
        write_json(args.json_output, payload)
    if args.csv_output:
        write_csv(
            args.csv_output,
            reverse_items,
            ["reverse_id", "source", "date", "url", "reverse_evidence", "impact", "response", "conclusion", "risk", "labels"],
        )

    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
