#!/usr/bin/env python3
"""Validate the P0 skill package structure."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "README.en.md",
    "agents/interface.yaml",
    "references/model-config-guide.md",
    "references/first-run-onboarding.md",
    "references/model-agent-catalog.md",
    "references/model-assignment.md",
    "references/eight-step-workflow.md",
    "references/workflow-gates.md",
    "references/platform-routing.md",
    "references/evidence-rules.md",
    "references/methodology-router.md",
    "references/commercial-prd-contract.md",
    "references/model-health-check.md",
    "references/community-evidence-scan.md",
    "references/community-platform-catalog.md",
    "references/workflow-orchestration.md",
    "references/real-run-playbook.md",
    "templates/model-config-status.md",
    "templates/model-setup-welcome.md",
    "templates/intent-card.md",
    "templates/evidence-pack.md",
    "templates/opportunity-assessment-report.md",
    "templates/commercial-opportunity-prd.md",
    "templates/model-pool.example.json",
    "templates/model-pool.providers.example.json",
    "templates/model-pool.real.example.json",
    "templates/community-sources.example.json",
    "templates/real-run-case.example.json",
    "scripts/check_model_pool.py",
    "scripts/setup_model_pool.py",
    "scripts/scan_community_evidence.py",
    "scripts/scan_reverse_evidence.py",
    "scripts/run_opportunity_workflow.py",
    "scripts/prepare_real_run.py",
    "scripts/simulate_user_flow.py",
    "scripts/validate_opportunity_prd.py",
    "tests/fixtures/mock_model_cli.py",
    "tests/fixtures/model-pool-cli.json",
    "tests/fixtures/model-pool-codex-only.json",
    "tests/fixtures/model-pool-missing-secret.json",
    "tests/fixtures/community-sources-local.json",
    "tests/fixtures/community-batch-sources-local.json",
    "tests/fixtures/community-sample-customer-service.md",
    "tests/fixtures/community-sample-customer-service-en.md",
    "tests/fixtures/community-batch/sample-cn.md",
    "tests/fixtures/community-batch/sample-en.md",
    "tests/fixtures/reverse-sources-local.json",
    "tests/fixtures/community-reverse-customer-service.md",
    "tests/fixtures/reverse-sources-go-local.json",
    "tests/fixtures/community-reverse-customer-service-go.md",
    "tests/fixtures/real-url-pages/positive.txt",
    "tests/fixtures/real-url-pages/reverse.txt",
    "tests/fixtures/one-line-idea-resume-outline.md",
    "tests/fixtures/nogo-trend-only.md",
    "tests/fixtures/go-customer-service.md",
    "tests/fixtures/community-codex-broad-pains.md",
    "tests/fixtures/community-codex-broad-sources-local.json",
    "tests/fixtures/community-codex-reverse.md",
    "tests/fixtures/community-codex-reverse-sources-local.json",
]

SKILL_REQUIRED_TERMS = [
    "Codex",
    "模型",
    "动态分工",
    "证据墙",
    "反向证据",
    "Gate",
    "机会评估报告",
    "商业化机会",
    "工程实施 PRD",
    "No-Go",
]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def validate_skill_frontmatter(errors: list[str]) -> None:
    text = read_text("SKILL.md")
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not match:
        errors.append("SKILL.md 缺少合法 YAML frontmatter")
        return

    frontmatter = match.group(1)
    if "name: BLCaptain Opportunity PRD Skill" not in frontmatter:
        errors.append("SKILL.md frontmatter name 必须是 BLCaptain Opportunity PRD Skill")
    if "description:" not in frontmatter:
        errors.append("SKILL.md frontmatter 缺少 description")
    if len(frontmatter) > 1400:
        errors.append("SKILL.md frontmatter 过长，触发描述应保持简洁")
    if re.search(r"\bTODO\b|\bTBD\b|待补充|待定", text, flags=re.I):
        errors.append("SKILL.md 不能包含未解决占位符")

    for term in SKILL_REQUIRED_TERMS:
        if term not in text:
            errors.append(f"SKILL.md 缺少关键术语：{term}")


def validate_interface(errors: list[str]) -> None:
    text = read_text("agents/interface.yaml")
    required = [
        "display_name:",
        "short_description:",
        "default_prompt:",
        "BLCaptain Opportunity PRD Skill",
        "canonical_format:",
    ]
    for marker in required:
        if marker not in text:
            errors.append(f"agents/interface.yaml 缺少 {marker}")


def validate_readmes(errors: list[str]) -> None:
    zh = read_text("README.md")
    en = read_text("README.en.md")
    for path, text in [("README.md", zh), ("README.en.md", en)]:
        if "BLCaptain Opportunity PRD Skill" not in text:
            errors.append(f"{path} 缺少正式 Skill 名称")
    if "README.en.md" not in zh:
        errors.append("README.md 缺少英文 README 链接")
    if "README.md" not in en:
        errors.append("README.en.md 缺少中文 README 链接")


def validate_references(errors: list[str]) -> None:
    gates = read_text("references/workflow-gates.md")
    for gate in [f"G{i}" for i in range(9)]:
        if gate not in gates:
            errors.append(f"workflow-gates.md 缺少 {gate}")

    assignment = read_text("references/model-assignment.md")
    if "不硬编码" not in read_text("SKILL.md") and "不写“某个固定模型必须负责长文本”" not in assignment:
        errors.append("动态模型分工规则没有明确禁止固定模型职责")

    evidence = read_text("references/evidence-rules.md")
    for marker in ["evidence_id", "URL", "日期", "用户原话", "商业信号", "reverse_id"]:
        if marker not in evidence:
            errors.append(f"evidence-rules.md 缺少 {marker}")

    first_run = read_text("references/first-run-onboarding.md")
    for marker in ["首次运行引导", "模型 Agent", "帮我接入", "配置完成前不进入机会分析"]:
        if marker not in first_run:
            errors.append(f"first-run-onboarding.md 缺少 {marker}")

    catalog = read_text("references/model-agent-catalog.md")
    for marker in ["OpenAI-compatible", "长文本 CLI", "代码/原型 CLI", "本地模型 CLI", "Codex 主持"]:
        if marker not in catalog:
            errors.append(f"model-agent-catalog.md 缺少 {marker}")


def validate_one_line_fixture(errors: list[str]) -> None:
    text = read_text("tests/fixtures/one-line-idea-resume-outline.md")
    required_order = [
        "模型配置状态",
        "意图卡",
        "平台路由",
        "证据墙模板",
        "机会评估报告",
    ]
    positions: list[int] = []
    for marker in required_order:
        pos = text.find(marker)
        if pos < 0:
            errors.append(f"一句话样例缺少 {marker}")
        positions.append(pos)

    if all(pos >= 0 for pos in positions) and positions != sorted(positions):
        errors.append("一句话样例输出顺序错误，必须先模型配置，再意图卡、平台路由、证据墙和机会评估报告")

    if re.search(r"^#\s*商业化机会 PRD|^##\s*0\.\s*商业速读卡", text, flags=re.M):
        errors.append("一句话样例不得直接生成商业化机会 PRD")


def validate_simulation_script(errors: list[str]) -> None:
    text = read_text("scripts/simulate_user_flow.py")
    for marker in [
        "未配置模型",
        "首次配置向导",
        "单模型低置信度",
        "No-Go",
        "Go",
        "模型健康检查",
        "社区证据扫描",
        "Cut-to-Go",
        "RUN_DIR",
        "user-flow-simulation",
    ]:
        if marker not in text:
            errors.append(f"simulate_user_flow.py 缺少演练标记：{marker}")


def validate_p1_files(errors: list[str]) -> None:
    model_script = read_text("scripts/check_model_pool.py")
    for marker in [
        "openai_compatible",
        "missing_secret",
        "cli",
        "api_key_env",
        "secret_ref",
        "resolve_model_secret",
        "build_openai_payload",
        "extract_assistant_text",
        "reasoning_content",
        "windows_dpapi",
        "redact",
        "discover_cli_candidates",
        "json-output",
    ]:
        if marker not in model_script:
            errors.append(f"check_model_pool.py 缺少 {marker}")

    setup_script = read_text("scripts/setup_model_pool.py")
    for marker in ["USER_CONFIG_PATH", "--init", "--doctor", "connect", "--store", "--prompt-key", "windows_dpapi", "secret_service", "keychain", "secret_ref", "max_tokens", "extra_body", "WELCOME_TEMPLATE", "health_payload"]:
        if marker not in setup_script:
            errors.append(f"setup_model_pool.py 缺少 {marker}")

    scan_script = read_text("scripts/scan_community_evidence.py")
    for marker in ["file", "url", "evidence_id", "Go-candidate", "用户原话", "商业信号"]:
        if marker not in scan_script:
            errors.append(f"scan_community_evidence.py 缺少 {marker}")


def validate_p2_files(errors: list[str]) -> None:
    platform_catalog = read_text("references/community-platform-catalog.md")
    for marker in ["Reddit", "Hacker News", "GitHub", "小红书", "Product Hunt", "不固定抓取平台", "L4"]:
        if marker not in platform_catalog:
            errors.append(f"community-platform-catalog.md 缺少 {marker}")

    scan_script = read_text("scripts/scan_community_evidence.py")
    for marker in ["directory", "json-output", "csv-output", "to_payload", "write_csv"]:
        if marker not in scan_script:
            errors.append(f"scan_community_evidence.py 缺少 P2 标记：{marker}")

    reverse_script = read_text("scripts/scan_reverse_evidence.py")
    for marker in ["reverse_id", "Pivot-required", "Pressure-test", "免费替代", "隐私合规", "csv-output"]:
        if marker not in reverse_script:
            errors.append(f"scan_reverse_evidence.py 缺少 {marker}")


def validate_p3_files(errors: list[str]) -> None:
    orchestration = read_text("references/workflow-orchestration.md")
    for marker in ["run_opportunity_workflow.py", "--run-discussion", "commercial-opportunity-prd.md", "workflow-summary", "Pivot-to-Go", "Cut-to-Go"]:
        if marker not in orchestration:
            errors.append(f"workflow-orchestration.md 缺少 {marker}")

    workflow_script = read_text("scripts/run_opportunity_workflow.py")
    for marker in [
        "run_workflow",
        "resolve_model_config",
        "assign_roles",
        "extract_assistant_text",
        "model-discussion.md",
        "opportunity-assessment.md",
        "commercial-opportunity-prd.md",
        "validate_generated_prd",
        "config_required_summary",
        "should_run_pivot_loop",
        "cluster_pain_points",
        "cut-to-go-assessment.md",
        "is_overbroad_opportunity",
        "build_model_setup_prd",
    ]:
        if marker not in workflow_script:
            errors.append(f"run_opportunity_workflow.py 缺少 {marker}")

    validator = read_text("scripts/validate_opportunity_prd.py")
    if "URL 或可追溯来源" not in validator:
        errors.append("validate_opportunity_prd.py 必须允许本地可追溯来源")


def validate_p4_files(errors: list[str]) -> None:
    playbook = read_text("references/real-run-playbook.md")
    for marker in ["prepare_real_run.py", "real-run-case.example.json", "--run-workflow", "--allow-local", "missing_secret"]:
        if marker not in playbook:
            errors.append(f"real-run-playbook.md 缺少 {marker}")

    prepare_script = read_text("scripts/prepare_real_run.py")
    for marker in ["fetch_public_url", "sources-positive.generated.json", "real-run-audit.md", "run_workflow", "missing_secret"]:
        if marker not in prepare_script:
            errors.append(f"prepare_real_run.py 缺少 {marker}")

    real_case = read_text("templates/real-run-case.example.json")
    for marker in ["positive_sources", "reverse_sources", "model_config"]:
        if marker not in real_case:
            errors.append(f"real-run-case.example.json 缺少 {marker}")


def validate_p5_files(errors: list[str]) -> None:
    contract = read_text("references/commercial-prd-contract.md")
    for marker in ["工程实施 PRD", "系统架构", "字段字典", "API 契约", "非功能需求", "开发任务拆分", "DoD"]:
        if marker not in contract:
            errors.append(f"commercial-prd-contract.md 缺少工程 PRD 标记：{marker}")

    template = read_text("templates/commercial-opportunity-prd.md")
    for marker in ["工程实施方案", "AI 风险标注方案", "API 契约", "异常流程", "部署运维", "开发任务拆分"]:
        if marker not in template:
            errors.append(f"commercial-opportunity-prd.md 模板缺少工程章节：{marker}")

    workflow_script = read_text("scripts/run_opportunity_workflow.py")
    for marker in ["工程实施 PRD", "API 契约", "错误码", "权限", "删除策略", "成本上限", "DoD"]:
        if marker not in workflow_script:
            errors.append(f"run_opportunity_workflow.py 缺少工程生成字段：{marker}")

    validator = read_text("scripts/validate_opportunity_prd.py")
    for marker in ["GO_ENGINEERING_MARKERS", "字段字典", "API 契约", "错误码", "DoD", "成本上限"]:
        if marker not in validator:
            errors.append(f"validate_opportunity_prd.py 缺少工程校验字段：{marker}")


def main() -> int:
    errors: list[str] = []

    for relative_path in REQUIRED_FILES:
        if not (ROOT / relative_path).exists():
            errors.append(f"缺少文件：{relative_path}")

    if not errors:
        validate_skill_frontmatter(errors)
        validate_interface(errors)
        validate_readmes(errors)
        validate_references(errors)
        validate_one_line_fixture(errors)
        validate_simulation_script(errors)
        validate_p1_files(errors)
        validate_p2_files(errors)
        validate_p3_files(errors)
        validate_p4_files(errors)
        validate_p5_files(errors)

    if errors:
        print("quick_validate failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("quick_validate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
