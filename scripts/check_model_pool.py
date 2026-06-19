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
HOST_METHOD = "codex_builtin"


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def redact(value: str | None) -> str:
    if not value:
        return ""
    return value[:2] + "***" + value[-2:] if len(value) > 4 else "***"


def is_placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    markers = ["填写", "your-", "replace-", "example command"]
    lowered = value.lower()
    return any(marker in lowered for marker in markers)


def check_cli(model: dict[str, Any], timeout: int) -> dict[str, Any]:
    command = model.get("command")
    if not command:
        return {"health": "missing_config", "reason": "缺少 command"}
    if is_placeholder(command):
        return {"health": "missing_config", "reason": "command 仍是占位内容"}

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
        reason = (result.stderr or result.stdout or "命令执行失败").strip()[:160]
        return {"health": "failed", "reason": reason, "latency_ms": elapsed_ms}

    output = result.stdout.strip()
    if not output:
        return {"health": "failed", "reason": "CLI 没有返回内容", "latency_ms": elapsed_ms}

    return {"health": "ok", "reason": "CLI 已返回文本", "latency_ms": elapsed_ms}


def check_openai_compatible(model: dict[str, Any], timeout: int) -> dict[str, Any]:
    base_url = str(model.get("base_url", "")).rstrip("/")
    model_name = model.get("model")
    if not base_url or not model_name:
        return {"health": "missing_config", "reason": "缺少 base_url 或 model"}
    if is_placeholder(base_url) or is_placeholder(model_name):
        return {"health": "missing_config", "reason": "base_url 或 model 仍是占位内容"}

    api_key_env = model.get("api_key_env")
    api_key = os.environ.get(api_key_env, "") if api_key_env else ""
    if not api_key:
        return {"health": "missing_secret", "reason": f"环境变量 {api_key_env or 'API_KEY'} 未设置"}

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
            "User-Agent": "BLCaptain-Opportunity-PRD-Skill/1.0",
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
    return {"health": "ok", "reason": "chat completions 已返回", "latency_ms": elapsed_ms}


def check_model(model: dict[str, Any], timeout: int) -> dict[str, Any]:
    method = model.get("method", "unknown")
    if method == "cli":
        result = check_cli(model, timeout)
    elif method == "openai_compatible":
        result = check_openai_compatible(model, timeout)
    elif method == HOST_METHOD:
        result = {
            "health": "host_available",
            "reason": "Codex 主持由当前运行时提供，不计入外部模型",
        }
    else:
        result = {"health": "failed", "reason": f"不支持的 method：{method}"}

    return {
        "id": model.get("id", model.get("display_name", "unknown")),
        "display_name": model.get("display_name", model.get("id", "unknown")),
        "method": method,
        "capability_tags": model.get("capability_tags", []),
        **result,
    }


def decide_mode(results: list[dict[str, Any]]) -> str:
    ok_count = external_ok_count(results)
    if ok_count == 0:
        return "config_required"
    if ok_count == 1:
        return "low_confidence"
    if ok_count <= 3:
        return "standard"
    return "heavy_discussion"


def external_ok_count(results: list[dict[str, Any]]) -> int:
    return sum(1 for item in results if item["method"] != HOST_METHOD and item["health"] == "ok")


def configured_external_count(results: list[dict[str, Any]]) -> int:
    return sum(1 for item in results if item["method"] != HOST_METHOD)


def codex_host_status(results: list[dict[str, Any]]) -> str:
    configured_host = any(item["method"] == HOST_METHOD for item in results)
    if configured_host:
        return "可主持（codex_builtin 仅作主持说明，不计入外部模型）"
    return "可主持（当前 Codex 运行时，不计入外部模型）"


def config_required_guidance() -> list[str]:
    return [
        "",
        "## 模型配置状态",
        "",
        "当前未检测到可用外部模型。",
        "",
        "Codex 可以主持流程，但为了完成多视角机会分析，建议至少配置 1 个外部模型；",
        "如果要做商业反方和结构化审查，建议配置 2-3 个。",
        "",
        "你可以选择以下任一方式：",
        "",
        "1. 让 Codex 帮你配置，推荐",
        "   - 直接说：帮我接入 DeepSeek / GLM / Claude / Gemini / Grok / 本地模型",
        "   - 如果你有 API Key，只告诉 Codex 你想使用的环境变量名，不要发送真实 key",
        "   - 如果你有 CLI，只提供本机非交互命令",
        "",
        "2. DeepSeek / GLM / Gemini / Grok / 其他 OpenAI-compatible 模型",
        "   - 需要：base_url、model 名称、API Key 环境变量名",
        "   - 不要把真实 API Key 写进配置文件",
        "",
        "3. Claude / Claude Code / 本地模型 CLI",
        "   - 需要：一个本机可执行命令",
        "   - 例如通过 CLI 返回一次文本响应即可",
        "",
        "4. 暂不配置",
        "   - 只用 Codex 主持做低置信度初筛",
        "   - 不声称完成多模型讨论",
        "",
        "请告诉我你有哪些模型：",
        "",
        "| 模型 | 调用方式 | 你想让它负责什么 |",
        "|---|---|---|",
        "| DeepSeek | OpenAI-compatible / CLI / 不确定 | 通用 / 结构化 / 反方 |",
        "| GLM | OpenAI-compatible / CLI / 不确定 | 长文本 / 结构化 / 代码 |",
        "| Claude | CLI / 不确定 | 长文本 / 反方 / 通用 |",
        "| Gemini | OpenAI-compatible / CLI / 不确定 | 外部趋势 / 多模态 / 通用 |",
        "| Grok | OpenAI-compatible / CLI / 不确定 | 社交视角 / 外部趋势 / 反方 |",
        "| 本地模型 | CLI / 不确定 | 通用 / 代码 / 成本敏感任务 |",
        "",
        "参考模板：`templates/model-pool.providers.example.json`。",
    ]


def to_markdown(config_path: Path, results: list[dict[str, Any]]) -> str:
    mode = decide_mode(results)
    external_ok = external_ok_count(results)
    external_configured = configured_external_count(results)
    lines = [
        "# 模型能力池健康检查",
        "",
        f"- 配置文件：{display_path(config_path)}",
        f"- 置信模式：{mode}",
        f"- 已配置外部模型数：{external_configured}",
        f"- 外部模型通过数：{external_ok}",
        f"- Codex 主持状态：{codex_host_status(results)}",
        "",
        "| 模型 | 方法 | 健康状态 | 能力标签 | 说明 |",
        "|---|---|---|---|---|",
    ]
    for item in results:
        tags = ", ".join(item.get("capability_tags", []))
        lines.append(
            f"| {item['display_name']} | {item['method']} | {item['health']} | {tags} | {item.get('reason', '')} |"
        )

    if not results:
        lines.append("| 未配置 | 无 | config_required | 无 | 请配置至少 1 个外部模型 |")

    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "- config_required：未检测到可用外部模型，只输出配置引导。",
            "- low_confidence：1 个外部模型可用，可以做低置信度初筛，但不得声称完成多模型讨论。",
            "- standard：2 到 3 个外部模型可用，可分配主分析、反方、结构化角色。",
            "- heavy_discussion：4 个及以上外部模型可用，可启用多视角讨论。",
        ]
    )
    if mode == "config_required":
        lines.extend(config_required_guidance())
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
