#!/usr/bin/env python3
"""First-run helper for the local model pool."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import check_model_pool


ROOT = Path(__file__).resolve().parents[1]
USER_CONFIG_DIR = Path.home() / ".config" / "blcaptain-opportunity-prd"
USER_CONFIG_PATH = USER_CONFIG_DIR / "model-pool.json"
WELCOME_TEMPLATE = ROOT / "templates" / "model-setup-welcome.md"


def display_path(path: Path) -> str:
    try:
        return str(path.expanduser().resolve().relative_to(ROOT))
    except ValueError:
        return str(path.expanduser())


def empty_config() -> dict[str, Any]:
    return {
        "version": "1.0",
        "description": "BLCaptain Opportunity PRD Skill 用户本地模型池。只保存环境变量名或本机 CLI 命令，不保存真实密钥。",
        "security_notes": [
            "不要把真实 API Key、token、cookie 写进本文件。",
            "OpenAI-compatible 模型只写 api_key_env。",
            "CLI 模型由本机命令、Keychain、密码管理器或 CLI 登录态负责鉴权。",
        ],
        "models": [],
    }


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_config()
    return json.loads(path.read_text(encoding="utf-8"))


def write_config(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def welcome_markdown(config_path: Path) -> str:
    text = WELCOME_TEMPLATE.read_text(encoding="utf-8")
    return text.replace("~/.config/blcaptain-opportunity-prd/model-pool.json", display_path(config_path))


def init_config(config_path: Path) -> str:
    if config_path.exists():
        return f"模型池已存在：{display_path(config_path)}"
    write_config(config_path, empty_config())
    return f"已创建空模型池：{display_path(config_path)}"


def doctor(config_path: Path, timeout: int) -> str:
    lines = [welcome_markdown(config_path), ""]
    if not config_path.exists():
        lines.extend(
            [
                "## 当前状态",
                "",
                f"- 模型池文件不存在：{display_path(config_path)}",
                "- 下一步：运行 `python3 scripts/setup_model_pool.py --init`，或让 Codex 帮你接入一个模型。",
                "",
            ]
        )
        results: list[dict[str, Any]] = []
    else:
        models = load_config(config_path).get("models", [])
        results = [check_model_pool.check_model(model, timeout) for model in models]
        lines.extend(["## 当前健康检查", "", check_model_pool.to_markdown(config_path, results), ""])

    payload = check_model_pool.health_payload(config_path, results)
    lines.extend(
        [
            "## 机器可读摘要",
            "",
            "```json",
            json.dumps(
                {
                    "mode": payload["mode"],
                    "configured_external_count": payload["configured_external_count"],
                    "external_ok_count": payload["external_ok_count"],
                    "config_path": payload["config_path"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            "```",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Initialize or inspect the BLCaptain model pool.")
    parser.add_argument("--config", default=str(USER_CONFIG_PATH), help="User model-pool JSON path.")
    parser.add_argument("--init", action="store_true", help="Create an empty local model-pool file if missing.")
    parser.add_argument("--doctor", action="store_true", help="Print first-run guidance and health-check summary.")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args(argv)

    config_path = Path(args.config).expanduser()
    if args.init:
        print(init_config(config_path))
    if args.doctor or not args.init:
        print(doctor(config_path, args.timeout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
