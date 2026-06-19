#!/usr/bin/env python3
"""Scan public URLs or local text files into an evidence-pack report."""

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

PAIN_KEYWORDS = [
    "手动",
    "每天",
    "半天",
    "截图",
    "表格",
    "麻烦",
    "太慢",
    "费时间",
    "漏掉",
    "manual",
    "manually",
    "spreadsheet",
    "screenshot",
    "copy",
    "export",
    "late",
    "save time",
    "too slow",
    "takes hours",
    "waste time",
]

COMMERCIAL_KEYWORDS = [
    "付费",
    "收费",
    "太贵",
    "预算",
    "成本",
    "报价",
    "订阅",
    "愿意买",
    "paid",
    "paying",
    "pay",
    "would pay",
    "expensive",
    "cheap",
    "budget",
    "price",
    "subscription",
    "stopped paying",
    "willing to pay",
]

DATE_PATTERN = re.compile(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b")


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


def has_any(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in lowered]


def extract_date(text: str) -> str:
    match = DATE_PATTERN.search(text)
    return match.group(0).replace("/", "-") if match else "未知"


def extract_platform(text: str, fallback: str) -> str:
    match = re.search(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\s+([^:：]{2,40})[:：]", text)
    if not match:
        return fallback
    platform = match.group(1).strip()
    platform = re.sub(r"^(?:[-*]\s*)", "", platform)
    return platform or fallback


def behavior_signal(text: str) -> str:
    matches = has_any(text, PAIN_KEYWORDS)
    return "、".join(matches[:3]) if matches else "未知"


def commercial_signal(text: str) -> str:
    matches = has_any(text, COMMERCIAL_KEYWORDS)
    return "、".join(matches[:3]) if matches else "未知"


def quote(text: str) -> str:
    text = re.sub(r"^\s*[-*]\s*", "", text).strip()
    return text[:180] + ("..." if len(text) > 180 else "")


def scan_sources(sources: list[Source], timeout: int) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    seen_quotes: set[str] = set()
    for source in sources:
        text = read_source(source, timeout)
        for block in split_blocks(text):
            pain = has_any(block, PAIN_KEYWORDS)
            commercial = has_any(block, COMMERCIAL_KEYWORDS)
            if not pain and not commercial:
                continue
            normalized_quote = quote(block)
            if normalized_quote in seen_quotes:
                continue
            seen_quotes.add(normalized_quote)
            evidence.append(
                {
                    "platform": extract_platform(block, source.platform),
                    "date": extract_date(block),
                    "url": source.url,
                    "quote": normalized_quote,
                    "behavior_signal": behavior_signal(block),
                    "commercial_signal": commercial_signal(block),
                    "level": "A" if pain and commercial and extract_date(block) != "未知" else "B",
                }
            )
    for index, item in enumerate(evidence, start=1):
        item["evidence_id"] = f"E-{index:03d}"
    return evidence


def evidence_stats(sources: list[Source], evidence: list[dict[str, str]]) -> dict[str, Any]:
    platforms = sorted({item["platform"] for item in evidence}) or sorted({source.platform for source in sources})
    valid_count = len([item for item in evidence if item["level"] == "A"])
    commercial_count = len([item for item in evidence if item["commercial_signal"] != "未知"])
    decision = "Watch"
    reason = "证据不足，需补充更多独立社区和反向证据。"
    if len(evidence) >= 5 and len(platforms) >= 2 and commercial_count >= 1:
        decision = "Go-candidate"
        reason = "正向证据和商业信号达到候选阈值，但仍需反向证据审查后才能 Go。"
    elif len(evidence) < 3:
        decision = "No-Go"
        reason = "有效证据少于 3 条。"

    return {
        "decision": decision,
        "reason": reason,
        "source_count": len(sources),
        "platform_count": len(platforms),
        "platforms": platforms,
        "evidence_count": len(evidence),
        "a_level_count": valid_count,
        "commercial_signal_count": commercial_count,
    }


def to_payload(idea: str, sources: list[Source], evidence: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "version": "1.0",
        "idea": idea,
        "stats": evidence_stats(sources, evidence),
        "sources": [source.__dict__ for source in sources],
        "evidence": evidence,
    }


def to_markdown(idea: str, sources: list[Source], evidence: list[dict[str, str]]) -> str:
    stats = evidence_stats(sources, evidence)

    lines = [
        "# 社区证据扫描报告",
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
            "## 评论证据墙",
            "",
            "| evidence_id | 平台 | 日期 | URL | 用户原话 | 行为信号 | 商业信号 | 等级 |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in evidence:
        lines.append(
            "| {evidence_id} | {platform} | {date} | {url} | {quote} | {behavior_signal} | {commercial_signal} | {level} |".format(
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
            f"| 来源数 | {stats['source_count']} |",
            f"| 独立平台数 | {stats['platform_count']} |",
            f"| 有效证据数 | {stats['evidence_count']} |",
            f"| A 级证据数 | {stats['a_level_count']} |",
            f"| 商业信号数 | {stats['commercial_signal_count']} |",
            "",
            "## 下一步",
            "",
            "- Go-candidate 仍需补充反向证据，不能直接生成商业化机会 PRD。",
            "- No-Go 或 Watch 时，先补更多近 30 天用户原话、手动行为和商业信号。",
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
    parser = argparse.ArgumentParser(description="Scan community evidence from public URLs, local files, or directories.")
    parser.add_argument("--idea", required=True, help="Product idea or opportunity hypothesis.")
    parser.add_argument("--sources", default=str(DEFAULT_SOURCES), help="JSON file with sources.")
    parser.add_argument("--output", help="Optional Markdown report path.")
    parser.add_argument("--json-output", help="Optional structured JSON output path.")
    parser.add_argument("--csv-output", help="Optional evidence CSV output path.")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args(argv)

    sources = parse_sources(Path(args.sources))
    evidence = scan_sources(sources, args.timeout)
    markdown = to_markdown(args.idea, sources, evidence)
    payload = to_payload(args.idea, sources, evidence)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
    if args.json_output:
        write_json(args.json_output, payload)
    if args.csv_output:
        write_csv(
            args.csv_output,
            evidence,
            ["evidence_id", "platform", "date", "url", "quote", "behavior_signal", "commercial_signal", "level"],
        )

    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
