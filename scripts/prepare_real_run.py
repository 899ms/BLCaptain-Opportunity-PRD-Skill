#!/usr/bin/env python3
"""Prepare a real-data opportunity run from public URLs and user model config."""

from __future__ import annotations

import argparse
import html.parser
import ipaddress
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import check_model_pool
import run_opportunity_workflow


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASE_CONFIG = ROOT / "templates" / "real-run-case.example.json"
DEFAULT_OUTPUT_DIR = ROOT / "tests" / "runs" / "real-run-prep"


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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def portable_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sanitize_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip())
    return cleaned.strip("-") or "source"


def is_local_host(hostname: str | None) -> bool:
    if not hostname:
        return True
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return address.is_loopback or address.is_private or address.is_link_local


def fetch_public_url(url: str, timeout: int, allow_local: bool) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return {"status": "failed", "reason": f"unsupported scheme {parsed.scheme or 'empty'}"}
    if is_local_host(parsed.hostname) and not allow_local:
        return {"status": "blocked", "reason": "local or private host requires --allow-local"}

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "opportunity-to-commercial-prd/1.0 real-run-prep"},
    )
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({})) if allow_local and is_local_host(parsed.hostname) else urllib.request
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(1_000_000)
            status_code = getattr(response, "status", 200)
            content_type = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        return {"status": "failed", "reason": f"http {exc.code}"}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"status": "failed", "reason": str(exc)[:200]}

    text = raw.decode("utf-8", errors="replace")
    if "html" in content_type or "<html" in text[:500].lower():
        parser = TextExtractor()
        parser.feed(text)
        text = parser.text()

    return {
        "status": "ok",
        "reason": "fetched",
        "status_code": status_code,
        "content_type": content_type,
        "byte_count": len(raw),
        "text": text,
    }


def snapshot_source(
    source: dict[str, Any],
    kind: str,
    output_dir: Path,
    timeout: int,
    allow_local: bool,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    source_id = source.get("id", f"{kind}-source")
    platform = source.get("platform", "unknown")
    source_type = source.get("type", "url")
    url = source.get("url", "")

    audit = {
        "id": source_id,
        "platform": platform,
        "kind": kind,
        "type": source_type,
        "url": url,
        "status": "pending",
        "reason": "",
    }

    if source_type in {"file", "directory"}:
        path = resolve_path(url)
        exists = path.exists()
        audit.update({"status": "ok" if exists else "failed", "reason": "local source" if exists else "missing local source"})
        if not exists:
            return None, audit
        return {"id": source_id, "platform": platform, "type": source_type, "url": str(path)}, audit

    if source_type != "url":
        audit.update({"status": "failed", "reason": f"unsupported source type {source_type}"})
        return None, audit

    fetched = fetch_public_url(url, timeout, allow_local)
    audit.update({key: value for key, value in fetched.items() if key != "text"})
    if fetched["status"] != "ok":
        return None, audit

    snapshot_path = output_dir / "raw" / kind / f"{sanitize_id(source_id)}.md"
    header = [
        f"# URL 快照：{platform}",
        "",
        f"- source_id：{source_id}",
        f"- original_url：{url}",
        f"- fetched_at：{time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- content_type：{fetched.get('content_type', '')}",
        "",
        "## 原始文本",
        "",
    ]
    write_text(snapshot_path, "\n".join(header) + fetched["text"])
    return {"id": source_id, "platform": platform, "type": "file", "url": portable_path(snapshot_path)}, audit


def prepare_sources(
    case: dict[str, Any],
    output_dir: Path,
    timeout: int,
    allow_local: bool,
) -> tuple[Path, Path, list[dict[str, Any]]]:
    generated_positive: list[dict[str, Any]] = []
    generated_reverse: list[dict[str, Any]] = []
    audit_items: list[dict[str, Any]] = []

    for source in case.get("positive_sources", []):
        generated, audit = snapshot_source(source, "positive", output_dir, timeout, allow_local)
        audit_items.append(audit)
        if generated:
            generated_positive.append(generated)

    for source in case.get("reverse_sources", []):
        generated, audit = snapshot_source(source, "reverse", output_dir, timeout, allow_local)
        audit_items.append(audit)
        if generated:
            generated_reverse.append(generated)

    positive_path = output_dir / "sources-positive.generated.json"
    reverse_path = output_dir / "sources-reverse.generated.json"
    write_json(positive_path, {"version": "1.0", "sources": generated_positive})
    write_json(reverse_path, {"version": "1.0", "sources": generated_reverse})
    return positive_path, reverse_path, audit_items


def model_health(model_config: Path, timeout: int) -> tuple[list[dict[str, Any]], str]:
    config = check_model_pool.load_json(model_config)
    results = [check_model_pool.check_model(model, timeout) for model in config.get("models", [])]
    return results, check_model_pool.to_markdown(model_config, results)


def audit_markdown(case: dict[str, Any], audit_items: list[dict[str, Any]], model_results: list[dict[str, Any]]) -> str:
    ok_sources = len([item for item in audit_items if item["status"] == "ok"])
    ok_models = len([item for item in model_results if item["health"] in {"ok", "manual"}])
    lines = [
        "# 真实运行准备报告",
        "",
        f"- 想法：{case.get('idea', '未填写')}",
        f"- 可用来源数：{ok_sources}/{len(audit_items)}",
        f"- 可用模型数：{ok_models}/{len(model_results)}",
        "",
        "## 来源审计",
        "",
        "| source_id | 类型 | 平台 | URL/路径 | 状态 | 说明 |",
        "|---|---|---|---|---|---|",
    ]
    for item in audit_items:
        lines.append(
            f"| {item['id']} | {item['type']} | {item['platform']} | {item['url']} | {item['status']} | {item.get('reason', '')} |"
        )
    lines.extend(
        [
            "",
            "## 模型审计",
            "",
            "| 模型 | 方法 | 健康状态 | 说明 |",
            "|---|---|---|---|",
        ]
    )
    for item in model_results:
        lines.append(f"| {item['display_name']} | {item['method']} | {item['health']} | {item.get('reason', '')} |")
    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "- 若来源不足，补充公开 URL、本地导出文件或用户粘贴样本。",
            "- 若模型为 `missing_secret`，只需要设置对应环境变量，不要把真实密钥写入 JSON。",
            "- 来源和模型都可用后，运行 P3 工作流生成机会评估；只有 Go 时生成 PRD。",
        ]
    )
    return "\n".join(lines)


def run_workflow(
    case: dict[str, Any],
    model_config: Path,
    positive_sources: Path,
    reverse_sources: Path,
    output_dir: Path,
    timeout: int,
    run_discussion: bool,
) -> dict[str, Any]:
    workflow_args = argparse.Namespace(
        idea=case.get("idea", ""),
        model_config=str(model_config),
        sources=str(positive_sources),
        reverse_sources=str(reverse_sources),
        output_dir=str(output_dir / "workflow"),
        timeout=timeout,
        run_discussion=run_discussion,
    )
    return run_opportunity_workflow.run_workflow(workflow_args)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Prepare a real opportunity run from public URLs and model config.")
    parser.add_argument("--case-config", default=str(DEFAULT_CASE_CONFIG), help="Real-run case JSON config.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for prepared artifacts.")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--allow-local", action="store_true", help="Allow localhost/private URLs for local testing.")
    parser.add_argument("--run-workflow", action="store_true", help="Run the P3 workflow after preparing sources.")
    parser.add_argument("--run-discussion", action="store_true", help="Invoke callable models during workflow.")
    args = parser.parse_args(argv)

    case_path = resolve_path(args.case_config)
    output_dir = Path(args.output_dir)
    case = load_json(case_path)
    model_config = resolve_path(case.get("model_config", "templates/model-pool.example.json"))

    positive_path, reverse_path, audit_items = prepare_sources(case, output_dir, args.timeout, args.allow_local)
    model_results, model_report = model_health(model_config, args.timeout)
    write_text(output_dir / "model-health.md", model_report)
    write_json(output_dir / "model-health.json", {"models": model_results, "mode": check_model_pool.decide_mode(model_results)})

    report = audit_markdown(case, audit_items, model_results)
    write_text(output_dir / "real-run-audit.md", report)
    write_json(
        output_dir / "real-run-audit.json",
        {
            "case_config": str(case_path),
            "idea": case.get("idea", ""),
            "positive_sources": str(positive_path),
            "reverse_sources": str(reverse_path),
            "source_audit": audit_items,
            "model_results": model_results,
        },
    )

    workflow_summary = None
    if args.run_workflow:
        workflow_summary = run_workflow(
            case,
            model_config,
            positive_path,
            reverse_path,
            output_dir,
            args.timeout,
            args.run_discussion,
        )

    print(f"真实运行准备完成：{output_dir}")
    print(f"来源配置：{positive_path} / {reverse_path}")
    if workflow_summary:
        print(f"工作流结果：{workflow_summary['decision']}，输出目录：{workflow_summary['output_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
