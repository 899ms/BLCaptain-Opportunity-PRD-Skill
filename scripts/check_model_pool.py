#!/usr/bin/env python3
"""Check a user-configured model pool without storing secrets."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "templates" / "model-pool.example.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def redact(value: str | None) -> str:
    if not value:
        return ""
    return value[:2] + "***" + value[-2:] if len(value) > 4 else "***"


def check_cli(model: dict[str, Any], timeout: int) -> dict[str, Any]:
    command = model.get("command")
    if not command:
        return {"health": "failed", "reason": "missing command"}

    start = time.time()
    try:
        result = subprocess.run(
            command,
            input=model.get("test_prompt", "ping"),
            text=True,
            shell=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"health": "failed", "reason": f"timeout>{timeout}s"}

    elapsed_ms = int((time.time() - start) * 1000)
    if result.returncode != 0:
        reason = (result.stderr or result.stdout or "command failed").strip()[:160]
        return {"health": "failed", "reason": reason, "latency_ms": elapsed_ms}

    output = result.stdout.strip()
    if not output:
        return {"health": "failed", "reason": "empty output", "latency_ms": elapsed_ms}

    return {"health": "ok", "reason": "cli returned output", "latency_ms": elapsed_ms}


def check_openai_compatible(model: dict[str, Any], timeout: int) -> dict[str, Any]:
    api_key_env = model.get("api_key_env")
    api_key = os.environ.get(api_key_env, "") if api_key_env else ""
    if not api_key:
        return {"health": "missing_secret", "reason": f"env {api_key_env or 'API_KEY'} not set"}

    base_url = str(model.get("base_url", "")).rstrip("/")
    model_name = model.get("model")
    if not base_url or not model_name:
        return {"health": "failed", "reason": "missing base_url or model"}

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": model.get("test_prompt", "ping")}],
        "max_tokens": int(model.get("max_tokens", 8)),
        "temperature": 0,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "opportunity-to-commercial-prd/1.0",
        },
    )

    start = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(2048)
    except urllib.error.HTTPError as exc:
        return {"health": "failed", "reason": f"http {exc.code}", "secret": redact(api_key)}
    except urllib.error.URLError as exc:
        return {"health": "failed", "reason": str(exc.reason)[:160], "secret": redact(api_key)}
    except TimeoutError:
        return {"health": "failed", "reason": f"timeout>{timeout}s", "secret": redact(api_key)}

    elapsed_ms = int((time.time() - start) * 1000)
    return {"health": "ok", "reason": "chat completions returned", "latency_ms": elapsed_ms}


def check_model(model: dict[str, Any], timeout: int) -> dict[str, Any]:
    method = model.get("method", "unknown")
    if method == "cli":
        result = check_cli(model, timeout)
    elif method == "openai_compatible":
        result = check_openai_compatible(model, timeout)
    elif method == "codex_builtin":
        result = {"health": "manual", "reason": "Codex built-in model is verified by current runtime"}
    else:
        result = {"health": "failed", "reason": f"unsupported method {method}"}

    return {
        "id": model.get("id", model.get("display_name", "unknown")),
        "display_name": model.get("display_name", model.get("id", "unknown")),
        "method": method,
        "capability_tags": model.get("capability_tags", []),
        **result,
    }


def decide_mode(results: list[dict[str, Any]]) -> str:
    ok_count = sum(1 for item in results if item["health"] in {"ok", "manual"})
    if ok_count == 0:
        return "config_required"
    if ok_count == 1:
        return "low_confidence"
    if ok_count <= 3:
        return "standard"
    return "heavy_discussion"


def to_markdown(config_path: Path, results: list[dict[str, Any]]) -> str:
    mode = decide_mode(results)
    ok_count = sum(1 for item in results if item["health"] in {"ok", "manual"})
    lines = [
        "# 模型能力池健康检查",
        "",
        f"- 配置文件：{config_path}",
        f"- 置信模式：{mode}",
        f"- 可用模型数：{ok_count}",
        "",
        "| 模型 | 方法 | 健康状态 | 能力标签 | 说明 |",
        "|---|---|---|---|---|",
    ]
    for item in results:
        tags = ", ".join(item.get("capability_tags", []))
        lines.append(
            f"| {item['display_name']} | {item['method']} | {item['health']} | {tags} | {item.get('reason', '')} |"
        )

    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "- config_required：只输出三步配置引导，不进入机会分析。",
            "- low_confidence：可以做单模型初筛，但不得声称完成多模型讨论。",
            "- standard：可分配主分析、反方、结构化角色。",
            "- heavy_discussion：可启用多视角讨论。",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Check configured model pool.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Path to model pool JSON config.")
    parser.add_argument("--output", help="Optional Markdown report path.")
    parser.add_argument("--timeout", type=int, default=20, help="Per-model timeout seconds.")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    config = load_json(config_path)
    models = config.get("models", [])
    results = [check_model(model, args.timeout) for model in models]
    markdown = to_markdown(config_path, results)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
    print(markdown)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
