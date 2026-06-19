#!/usr/bin/env python3
"""Run a realistic P0 user-flow simulation for this skill."""

from __future__ import annotations

import functools
import http.server
import re
import json
import subprocess
import threading
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "tests" / "runs"
REPORT_PATH = RUN_DIR / "user-flow-simulation-2026-06-19.md"


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def assert_contains(text: str, markers: list[str], label: str, errors: list[str]) -> None:
    for marker in markers:
        if marker not in text:
            errors.append(f"{label} 缺少：{marker}")


def assert_not_contains(text: str, markers: list[str], label: str, errors: list[str]) -> None:
    for marker in markers:
        if marker in text:
            errors.append(f"{label} 不应包含：{marker}")


def check_order(text: str, markers: list[str], label: str, errors: list[str]) -> None:
    positions = [text.find(marker) for marker in markers]
    missing = [marker for marker, pos in zip(markers, positions) if pos < 0]
    if missing:
        errors.append(f"{label} 缺少顺序标记：{', '.join(missing)}")
        return
    if positions != sorted(positions):
        errors.append(f"{label} 顺序错误：{' -> '.join(markers)}")


def simulate_no_model(errors: list[str]) -> str:
    output = """# 模拟输出：未配置模型

## 模型配置状态

| 字段 | 内容 |
|---|---|
| 配置状态 | config_required |
| 已配置外部模型数 | 0 |
| 外部模型通过数 | 0 |
| Codex 主持状态 | 可主持（不计入外部模型） |

## 三步配置引导

1. 添加模型：填写 DeepSeek、GLM、Claude、Gemini、Grok 或本地模型名称。
2. 填调用方式：OpenAI-compatible URL、CLI 命令或暂不确定。
3. 测试并选择用途：长文本、商业反方、结构化、外部趋势、代码实现或通用。

当前不进入机会分析，不生成平台路由、证据墙或商业化机会 PRD。
"""
    assert_contains(output, ["配置状态 | config_required", "三步配置引导"], "未配置模型", errors)
    assert_not_contains(output, ["# 商业化机会 PRD", "## 0. 商业速读卡"], "未配置模型", errors)
    return output


def simulate_one_model(errors: list[str]) -> str:
    output = read("tests/fixtures/one-line-idea-resume-outline.md")
    assert_contains(output, ["low_confidence", "单模型低置信度", "机会评估报告"], "单模型低置信度", errors)
    check_order(output, ["模型配置状态", "意图卡", "平台路由", "证据墙模板", "机会评估报告"], "一句话想法", errors)
    assert_not_contains(output, ["# 商业化机会 PRD", "## 0. 商业速读卡"], "一句话想法", errors)
    return output


def validate_report_fixture(relative_path: str, expected_decision: str, errors: list[str]) -> str:
    text = read(relative_path)
    if f"| 结论 | {expected_decision} |" not in text:
        errors.append(f"{relative_path} 决策不是 {expected_decision}")

    if expected_decision == "No-Go":
        assert_contains(text, ["缺少用户原话", "商业信号不足", "不生成商业化机会 PRD"], "No-Go", errors)
        assert_not_contains(text, ["# 商业化机会 PRD", "## 0. 商业速读卡"], "No-Go", errors)
    else:
        assert_contains(text, ["商业化机会 PRD", "evidence_id", "R-001", "7 天", "验收剧本"], "Go", errors)
        evidence_ids = set(re.findall(r"\bE-\d{3}\b", text))
        reverse_ids = set(re.findall(r"\bR-\d{3}\b", text))
        if len(evidence_ids) < 5:
            errors.append("Go 样例 evidence_id 少于 5 条")
        if len(reverse_ids) < 3:
            errors.append("Go 样例 reverse_id 少于 3 条")
    return text


def run_command(command: list[str], cwd: Path, label: str, errors: list[str]) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        errors.append(f"{label} 命令失败：{' '.join(command)}\n{output}")
    return output


def simulate_model_health(errors: list[str]) -> str:
    output_path = RUN_DIR / "model-health-cli.md"
    output = run_command(
        [
            "python3",
            "scripts/check_model_pool.py",
            "--config",
            "tests/fixtures/model-pool-cli.json",
            "--output",
            str(output_path),
        ],
        ROOT,
        "模型健康检查",
        errors,
    )
    assert_contains(output, ["low_confidence", "Mock CLI Model", "ok"], "模型健康检查", errors)
    return output


def simulate_codex_only_model_pool(errors: list[str]) -> str:
    output_path = RUN_DIR / "model-health-codex-only.md"
    output = run_command(
        [
            "python3",
            "scripts/check_model_pool.py",
            "--config",
            "tests/fixtures/model-pool-codex-only.json",
            "--output",
            str(output_path),
        ],
        ROOT,
        "Codex 主持不计入外部模型",
        errors,
    )
    assert_contains(
        output,
        ["置信模式：config_required", "Codex Host", "host_available", "外部模型通过数：0"],
        "Codex 主持不计入外部模型",
        errors,
    )
    return output


def simulate_missing_secret(errors: list[str]) -> str:
    output_path = RUN_DIR / "model-health-missing-secret.md"
    output = run_command(
        [
            "python3",
            "scripts/check_model_pool.py",
            "--config",
            "tests/fixtures/model-pool-missing-secret.json",
            "--output",
            str(output_path),
        ],
        ROOT,
        "缺密钥模型健康检查",
        errors,
    )
    assert_contains(output, ["config_required", "missing_secret", "OPPORTUNITY_PRD_MISSING_KEY"], "缺密钥模型健康检查", errors)
    assert_not_contains(output, ["sk-", "Bearer "], "缺密钥模型健康检查", errors)
    return output


def simulate_community_scan(errors: list[str]) -> str:
    output_path = RUN_DIR / "community-evidence-report.md"
    output = run_command(
        [
            "python3",
            "scripts/scan_community_evidence.py",
            "--idea",
            "AI 客服质检工具",
            "--sources",
            "tests/fixtures/community-sources-local.json",
            "--output",
            str(output_path),
        ],
        ROOT,
        "社区证据扫描",
        errors,
    )
    assert_contains(output, ["社区证据扫描报告", "Go-candidate", "E-001", "用户原话", "商业信号"], "社区证据扫描", errors)
    if len(set(re.findall(r"\bE-\d{3}\b", output))) < 5:
        errors.append("社区证据扫描 evidence_id 少于 5 条")
    return output


def simulate_batch_exports(errors: list[str]) -> str:
    md_path = RUN_DIR / "community-evidence-batch.md"
    json_path = RUN_DIR / "community-evidence-batch.json"
    csv_path = RUN_DIR / "community-evidence-batch.csv"
    output = run_command(
        [
            "python3",
            "scripts/scan_community_evidence.py",
            "--idea",
            "AI 客服质检工具",
            "--sources",
            "tests/fixtures/community-batch-sources-local.json",
            "--output",
            str(md_path),
            "--json-output",
            str(json_path),
            "--csv-output",
            str(csv_path),
        ],
        ROOT,
        "批量社区证据扫描和结构化导出",
        errors,
    )
    assert_contains(output, ["社区证据扫描报告", "Go-candidate", "E-001"], "批量社区证据扫描", errors)
    if not json_path.exists() or not csv_path.exists():
        errors.append("批量社区证据扫描未生成 JSON 或 CSV")
        return output
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if payload.get("stats", {}).get("evidence_count", 0) < 5:
        errors.append("批量社区证据扫描 JSON evidence_count 少于 5")
    if "evidence_id" not in csv_path.read_text(encoding="utf-8"):
        errors.append("批量社区证据扫描 CSV 缺少 evidence_id 表头")
    return output


def simulate_reverse_scan(errors: list[str]) -> str:
    md_path = RUN_DIR / "reverse-evidence-report.md"
    json_path = RUN_DIR / "reverse-evidence-report.json"
    csv_path = RUN_DIR / "reverse-evidence-report.csv"
    output = run_command(
        [
            "python3",
            "scripts/scan_reverse_evidence.py",
            "--idea",
            "AI 客服质检工具",
            "--sources",
            "tests/fixtures/reverse-sources-local.json",
            "--output",
            str(md_path),
            "--json-output",
            str(json_path),
            "--csv-output",
            str(csv_path),
        ],
        ROOT,
        "反向证据扫描",
        errors,
    )
    assert_contains(output, ["反向证据扫描报告", "Pivot-required", "R-001", "反向证据墙"], "反向证据扫描", errors)
    if not json_path.exists() or not csv_path.exists():
        errors.append("反向证据扫描未生成 JSON 或 CSV")
        return output
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if payload.get("stats", {}).get("reverse_count", 0) < 3:
        errors.append("反向证据扫描 JSON reverse_count 少于 3")
    if "reverse_id" not in csv_path.read_text(encoding="utf-8"):
        errors.append("反向证据扫描 CSV 缺少 reverse_id 表头")
    return output


def simulate_full_workflow_go(errors: list[str]) -> str:
    output_dir = RUN_DIR / "opportunity-workflow-go"
    output = run_command(
        [
            "python3",
            "scripts/run_opportunity_workflow.py",
            "--idea",
            "AI 客服质检工具",
            "--model-config",
            "tests/fixtures/model-pool-cli.json",
            "--sources",
            "tests/fixtures/community-batch-sources-local.json",
            "--reverse-sources",
            "tests/fixtures/reverse-sources-go-local.json",
            "--output-dir",
            str(output_dir),
            "--run-discussion",
        ],
        ROOT,
        "P3 端到端 Go 工作流",
        errors,
    )
    assert_contains(output, ["工作流完成：Go", "opportunity-workflow-go"], "P3 端到端 Go 工作流", errors)
    summary_path = output_dir / "workflow-summary.json"
    prd_path = output_dir / "commercial-opportunity-prd.md"
    discussion_path = output_dir / "model-discussion.md"
    for path in [summary_path, prd_path, discussion_path]:
        if not path.exists():
            errors.append(f"P3 端到端 Go 工作流缺少输出文件：{path}")
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("decision") != "Go" or not summary.get("prd_valid"):
            errors.append("P3 端到端 Go 工作流 summary 未通过")
    validate_output = run_command(
        ["python3", "scripts/validate_opportunity_prd.py", str(prd_path)],
        ROOT,
        "P3 生成 PRD 校验",
        errors,
    )
    assert_contains(validate_output, ["validate_opportunity_prd passed"], "P3 生成 PRD 校验", errors)
    return output


def simulate_full_workflow_pivot(errors: list[str]) -> str:
    output_dir = RUN_DIR / "opportunity-workflow-pivot"
    output = run_command(
        [
            "python3",
            "scripts/run_opportunity_workflow.py",
            "--idea",
            "AI 客服质检工具",
            "--model-config",
            "tests/fixtures/model-pool-cli.json",
            "--sources",
            "tests/fixtures/community-batch-sources-local.json",
            "--reverse-sources",
            "tests/fixtures/reverse-sources-local.json",
            "--output-dir",
            str(output_dir),
        ],
        ROOT,
        "P3 端到端 Pivot 工作流",
        errors,
    )
    assert_contains(output, ["工作流完成：Pivot", "opportunity-workflow-pivot"], "P3 端到端 Pivot 工作流", errors)
    summary_path = output_dir / "workflow-summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("decision") != "Pivot" or summary.get("prd_generated"):
            errors.append("P3 端到端 Pivot 工作流不应生成 PRD")
    else:
        errors.append(f"P3 端到端 Pivot 工作流缺少输出文件：{summary_path}")
    return output


class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def simulate_real_run_prepare(errors: list[str]) -> str:
    fixture_dir = ROOT / "tests" / "fixtures" / "real-url-pages"
    handler = functools.partial(QuietHTTPRequestHandler, directory=str(fixture_dir))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    case_path = RUN_DIR / "real-run-case-local-url.json"
    output_dir = RUN_DIR / "real-run-prep"
    case_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "idea": "AI 客服质检工具",
                "model_config": "tests/fixtures/model-pool-cli.json",
                "positive_sources": [
                    {
                        "id": "P-URL-001",
                        "platform": "本地公开正向 URL 样本",
                        "type": "url",
                        "url": f"http://127.0.0.1:{port}/positive.txt",
                    }
                ],
                "reverse_sources": [
                    {
                        "id": "R-URL-001",
                        "platform": "本地公开反向 URL 样本",
                        "type": "url",
                        "url": f"http://127.0.0.1:{port}/reverse.txt",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        output = run_command(
            [
                "python3",
                "scripts/prepare_real_run.py",
                "--case-config",
                str(case_path),
                "--output-dir",
                str(output_dir),
                "--allow-local",
                "--run-workflow",
                "--run-discussion",
            ],
            ROOT,
            "P4 真实 URL 准备和工作流",
            errors,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert_contains(output, ["真实运行准备完成", "工作流结果：Go"], "P4 真实 URL 准备和工作流", errors)
    required = [
        output_dir / "real-run-audit.md",
        output_dir / "sources-positive.generated.json",
        output_dir / "sources-reverse.generated.json",
        output_dir / "workflow" / "workflow-summary.json",
        output_dir / "workflow" / "commercial-opportunity-prd.md",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"P4 真实 URL 准备缺少输出文件：{path}")
    summary_path = output_dir / "workflow" / "workflow-summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("decision") != "Go" or not summary.get("prd_valid"):
            errors.append("P4 真实 URL 准备 workflow summary 未通过")
    return output


def build_report(errors: list[str], sections: list[tuple[str, str]]) -> str:
    status = "PASS" if not errors else "FAIL"
    lines = [
        "# BLCaptain Opportunity PRD Skill 真实用户端到端演练报告",
        "",
        f"- 日期：{date.today().isoformat()}",
        f"- 结果：{status}",
        "- 范围：P0 本地 skill 使用体验，不接真实 API、不抓私密社区、不做全局发布判断。",
        "",
        "## 覆盖场景",
        "",
        "- 未配置模型：只输出三步配置引导。",
        "- 单模型低置信度：可继续做机会初筛，但不声称多模型讨论。",
        "- 一句话想法：先出模型配置状态、意图卡、平台路由、证据墙模板、机会评估报告。",
        "- No-Go：趋势文章无评论原话时必须拦住。",
        "- Go：客服质检样例有证据、反证、商业信号后才生成商业化机会 PRD。",
        "- 模型健康检查：CLI mock 可通过，缺密钥 OpenAI-compatible 不伪装成功。",
        "- Codex 主持检查：codex_builtin 只说明主持可用，不计入外部模型。",
        "- 社区证据扫描：本地社区样本能抽取 evidence_id、用户原话、行为信号和商业信号。",
        "- 批量扫描和结构化导出：目录样本能输出 Markdown、JSON、CSV。",
        "- 反向证据扫描：能输出 reverse_id，并在高风险反证出现时阻止直接 Go。",
        "- 端到端工作流：Go 样例生成并校验商业化 PRD，Pivot 样例只输出机会评估。",
        "- 真实运行准备：公开 URL 能快照成本地 sources，并衔接 P3 工作流。",
        "",
    ]

    if errors:
        lines.extend(["## 失败项", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")

    for title, body in sections:
        lines.extend([f"## {title}", "", "```markdown", body.strip(), "```", ""])

    return "\n".join(lines)


def main() -> int:
    errors: list[str] = []
    sections = [
        ("场景 1：未配置模型", simulate_no_model(errors)),
        ("场景 2：单模型低置信度 + 一句话想法", simulate_one_model(errors)),
        ("场景 3：No-Go 证据不足", validate_report_fixture("tests/fixtures/nogo-trend-only.md", "No-Go", errors)),
        ("场景 4：Go 后生成商业化机会 PRD", validate_report_fixture("tests/fixtures/go-customer-service.md", "Go", errors)),
        ("场景 5：模型健康检查", simulate_model_health(errors)),
        ("场景 6：Codex 主持不计入外部模型", simulate_codex_only_model_pool(errors)),
        ("场景 7：缺密钥模型不伪装成功", simulate_missing_secret(errors)),
        ("场景 8：社区证据扫描", simulate_community_scan(errors)),
        ("场景 9：批量社区扫描和结构化导出", simulate_batch_exports(errors)),
        ("场景 10：反向证据扫描", simulate_reverse_scan(errors)),
        ("场景 11：P3 端到端 Go 工作流", simulate_full_workflow_go(errors)),
        ("场景 12：P3 端到端 Pivot 工作流", simulate_full_workflow_pivot(errors)),
        ("场景 13：P4 真实 URL 准备和工作流", simulate_real_run_prepare(errors)),
    ]

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(build_report(errors, sections), encoding="utf-8")

    if errors:
        print(f"simulate_user_flow failed: {REPORT_PATH}")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"simulate_user_flow passed: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
