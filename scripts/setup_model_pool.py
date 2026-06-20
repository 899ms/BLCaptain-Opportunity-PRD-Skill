#!/usr/bin/env python3
"""First-run helper for the local model pool."""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import shutil
import sys
import subprocess
from pathlib import Path
from typing import Any

import check_model_pool


ROOT = Path(__file__).resolve().parents[1]
USER_CONFIG_DIR = Path.home() / ".config" / "blcaptain-opportunity-prd"
USER_CONFIG_PATH = USER_CONFIG_DIR / "model-pool.json"
WELCOME_TEMPLATE = ROOT / "templates" / "model-setup-welcome.md"
SECRET_SERVICE = "blcaptain-opportunity-prd"
PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "deepseek": {
        "id": "deepseek-main",
        "display_name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-pro",
        "env": "DEEPSEEK_API_KEY",
        "capability_tags": ["general", "structure", "commercial_reverse"],
        "max_tokens": 1536,
        "extra_body": {"thinking": {"type": "disabled"}},
    },
    "glm": {
        "id": "glm-main",
        "display_name": "GLM",
        "base_url": "https://open.bigmodel.cn/api/coding/paas/v4",
        "model": "GLM-5.2",
        "env": "GLM_API_KEY",
        "capability_tags": ["long_context", "structure", "chinese_context"],
        "max_tokens": 1536,
        "extra_body": {"thinking": {"type": "disabled"}},
    },
    "gemini": {
        "id": "gemini-main",
        "display_name": "Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-3.5-flash",
        "env": "GEMINI_API_KEY",
        "capability_tags": ["external_trend", "general", "multimodal"],
        "max_tokens": 1536,
        "extra_body": {"thinking": {"type": "disabled"}},
    },
    "grok": {
        "id": "grok-main",
        "display_name": "Grok",
        "base_url": "https://api.x.ai/v1",
        "model": "grok-4.3",
        "env": "GROK_API_KEY",
        "capability_tags": ["social", "external_trend", "commercial_reverse"],
        "max_tokens": 1536,
        "extra_body": {"thinking": {"type": "disabled"}},
    },
}


def display_path(path: Path) -> str:
    try:
        return str(path.expanduser().resolve().relative_to(ROOT))
    except ValueError:
        return str(path.expanduser())


def empty_config() -> dict[str, Any]:
    return {
        "version": "1.0",
        "description": "BLCaptain Opportunity PRD Skill 用户本地模型池。只保存 secret_ref、环境变量名或本机 CLI 命令，不保存真实密钥。",
        "security_notes": [
            "不要把真实 API Key、token、cookie 写进本文件。",
            "OpenAI-compatible 模型优先写 secret_ref，由本机安全凭据存储保存真实 Key。",
            "CLI 模型由本机命令、系统安全凭据、密码管理器或 CLI 登录态负责鉴权。",
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


def windows_secret_file() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home()))
    return base / "BLCaptain Opportunity PRD Skill" / "secrets.json"


def windows_dpapi_protect(secret: str) -> bytes:
    if sys.platform != "win32":
        raise RuntimeError("windows_dpapi 只支持 Windows")
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    data = secret.encode("utf-8")
    in_buffer = ctypes.create_string_buffer(data)
    in_blob = DATA_BLOB(len(data), ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_ubyte)))
    out_blob = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise RuntimeError("Windows DPAPI 加密失败")
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def choose_store(requested: str) -> str:
    if requested != "auto":
        return requested
    if sys.platform == "darwin" and shutil.which("security"):
        return "keychain"
    if sys.platform == "win32":
        return "windows_dpapi"
    if shutil.which("secret-tool"):
        return "secret_service"
    return "env"


def store_macos_keychain(service: str, account: str, secret: str) -> None:
    subprocess.run(
        ["security", "add-generic-password", "-U", "-s", service, "-a", account, "-w", secret],
        check=True,
        text=True,
        capture_output=True,
        timeout=10,
    )


def store_secret_service(service: str, account: str, secret: str) -> None:
    if not shutil.which("secret-tool"):
        raise RuntimeError("未发现 secret-tool")
    subprocess.run(
        ["secret-tool", "store", "--label", "BLCaptain Opportunity PRD Skill Model Key", "service", service, "account", account],
        input=secret,
        check=True,
        text=True,
        capture_output=True,
        timeout=10,
    )


def store_windows_dpapi(account: str, secret: str) -> None:
    path = windows_secret_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, str] = {}
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    payload[account] = base64.b64encode(windows_dpapi_protect(secret)).decode("ascii")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_secret_from_args(args: argparse.Namespace) -> str:
    if args.api_key_stdin:
        return sys.stdin.read().strip()
    if args.prompt_key:
        return getpass.getpass("请输入 API Key（不会显示）：").strip()
    return ""


def secret_ref_for_store(store: str, account: str, env_name: str, secret: str, dry_run: bool) -> tuple[dict[str, str], list[str]]:
    messages: list[str] = []
    if store == "env":
        return {"type": "env", "env": env_name}, [f"使用环境变量 `{env_name}`；未保存真实 Key。"]
    if not secret and not dry_run:
        raise ValueError("需要 API Key。推荐加 `--prompt-key` 进行隐藏输入，或用 `--api-key-stdin` 从标准输入传入。")

    if store == "keychain":
        if not dry_run:
            store_macos_keychain(SECRET_SERVICE, account, secret)
        messages.append("已使用 macOS Keychain 保存 Key。" if not dry_run else "将使用 macOS Keychain 保存 Key。")
        return {"type": "keychain", "service": SECRET_SERVICE, "account": account}, messages
    if store == "windows_dpapi":
        if not dry_run:
            store_windows_dpapi(account, secret)
        messages.append("已使用 Windows DPAPI 用户级加密保存 Key。" if not dry_run else "将使用 Windows DPAPI 用户级加密保存 Key。")
        return {"type": "windows_dpapi", "account": account}, messages
    if store == "secret_service":
        if not dry_run:
            store_secret_service(SECRET_SERVICE, account, secret)
        messages.append("已使用 Linux Secret Service 保存 Key。" if not dry_run else "将使用 Linux Secret Service 保存 Key。")
        return {"type": "secret_service", "service": SECRET_SERVICE, "account": account}, messages
    raise ValueError(f"不支持的存储方式：{store}")


def upsert_model(config: dict[str, Any], model: dict[str, Any]) -> None:
    models = config.setdefault("models", [])
    for index, item in enumerate(models):
        if item.get("id") == model["id"]:
            models[index] = model
            return
    models.append(model)


def connect_provider(args: argparse.Namespace) -> str:
    provider = args.provider.lower()
    if provider not in PROVIDER_PRESETS:
        known = " / ".join(PROVIDER_PRESETS)
        raise ValueError(f"暂不支持的模型：{args.provider}。可用：{known}，或使用 CLI 模型配置。")

    preset = PROVIDER_PRESETS[provider]
    config_path = Path(args.config).expanduser()
    config = load_config(config_path)
    store = choose_store(args.store)
    secret = read_secret_from_args(args)
    env_name = args.api_key_env or preset["env"]
    model_id = args.id or preset["id"]
    secret_ref, store_messages = secret_ref_for_store(store, model_id, env_name, secret, args.dry_run)
    model = {
        "id": model_id,
        "display_name": args.display_name or preset["display_name"],
        "method": "openai_compatible",
        "base_url": args.base_url or preset["base_url"],
        "model": args.model or preset["model"],
        "secret_ref": secret_ref,
        "capability_tags": preset["capability_tags"],
        "test_prompt": "ping",
        "max_tokens": args.max_tokens or preset.get("max_tokens", 1536),
        "extra_body": preset.get("extra_body", {}),
    }

    if args.keep_env_alias:
        model["api_key_env"] = env_name

    if not args.dry_run:
        upsert_model(config, model)
        write_config(config_path, config)

    lines = [
        "# 模型接入结果",
        "",
        f"- 模型：{model['display_name']}",
        f"- 配置文件：{display_path(config_path)}",
        f"- 存储方式：{store}",
        f"- base_url：{model['base_url']}",
        f"- model：{model['model']}",
        "- 真实 Key：未写入模型池 JSON、未输出到报告。",
        "",
        "## 安全存储",
        "",
    ]
    lines.extend(f"- {message}" for message in store_messages)
    if args.dry_run:
        lines.extend(["", "当前是 dry-run，没有写入配置或保存 Key。"])
    else:
        lines.extend(
            [
                "",
                "下一步运行：",
                "",
                f"`python3 scripts/check_model_pool.py --config {display_path(config_path)}`",
            ]
        )
    return "\n".join(lines)


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
    if argv and argv[0] == "connect":
        parser = argparse.ArgumentParser(description="Connect an OpenAI-compatible model with local secure secret storage.")
        parser.add_argument("provider", help="deepseek / glm / gemini / grok")
        parser.add_argument("--config", default=str(USER_CONFIG_PATH), help="User model-pool JSON path.")
        parser.add_argument("--store", default="auto", choices=["auto", "keychain", "windows_dpapi", "secret_service", "env"], help="Where to keep the real API key.")
        parser.add_argument("--prompt-key", action="store_true", help="Prompt for API key with hidden terminal input.")
        parser.add_argument("--api-key-stdin", action="store_true", help="Read API key from stdin. Use only when the caller can avoid logging it.")
        parser.add_argument("--api-key-env", help="Environment variable name used when --store env or as an alias.")
        parser.add_argument("--base-url", help="Override default OpenAI-compatible base URL.")
        parser.add_argument("--model", help="Override default model id.")
        parser.add_argument("--max-tokens", type=int, help="Override max_tokens for health checks and short discussions.")
        parser.add_argument("--id", help="Override model id in model pool.")
        parser.add_argument("--display-name", help="Override display name.")
        parser.add_argument("--keep-env-alias", action="store_true", help="Also keep api_key_env in the model entry as a fallback hint.")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be written without saving secrets or config.")
        args = parser.parse_args(argv[1:])
        try:
            print(connect_provider(args))
        except (ValueError, RuntimeError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            print(f"模型接入失败：{exc}", file=sys.stderr)
            return 2
        return 0

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
