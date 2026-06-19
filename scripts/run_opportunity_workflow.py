#!/usr/bin/env python3
"""Run the full opportunity-to-commercial-PRD workflow."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import textwrap
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import check_model_pool
import scan_community_evidence
import scan_reverse_evidence
import validate_opportunity_prd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_CONFIG = ROOT / "templates" / "model-pool.example.json"
DEFAULT_SOURCES = ROOT / "templates" / "community-sources.example.json"
RUN_DIR = ROOT / "tests" / "runs" / "opportunity-workflow"

ROLE_ORDER = ["主分析", "商业反方", "结构化审查", "长文本理解", "外部视角", "代码实现"]
ROLE_TAGS = {
    "主分析": ["general", "long_context", "structure"],
    "商业反方": ["commercial_reverse", "business", "finance"],
    "结构化审查": ["structure", "general"],
    "长文本理解": ["long_context", "general"],
    "外部视角": ["external_trend", "social", "general"],
    "代码实现": ["code", "file_generation", "validation"],
}


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_model_config(config_path: Path) -> list[dict[str, Any]]:
    return check_model_pool.load_json(config_path).get("models", [])


def model_health(config_path: Path, timeout: int) -> tuple[list[dict[str, Any]], str]:
    models = load_model_config(config_path)
    results = [check_model_pool.check_model(model, timeout) for model in models]
    return results, check_model_pool.to_markdown(config_path, results)


def available_models(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in results if item["health"] in {"ok", "manual"}]


def score_role(model: dict[str, Any], role: str) -> int:
    tags = set(model.get("capability_tags", []))
    return sum(1 for tag in ROLE_TAGS[role] if tag in tags)


def assign_roles(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    models = available_models(results)
    if not models:
        return []

    role_count = min(len(ROLE_ORDER), max(1, len(models)))
    if len(models) == 2:
        roles = ["主分析", "商业反方"]
    elif len(models) == 3:
        roles = ["主分析", "商业反方", "结构化审查"]
    else:
        roles = ROLE_ORDER[:role_count]

    assignments: list[dict[str, str]] = []
    for index, role in enumerate(roles):
        ranked = sorted(models, key=lambda item: (score_role(item, role), -index), reverse=True)
        model = ranked[index % len(ranked)] if len(ranked) > index else ranked[0]
        basis = "能力标签匹配" if score_role(model, role) else "可用模型轮转"
        assignments.append(
            {
                "model_id": model["id"],
                "display_name": model["display_name"],
                "method": model["method"],
                "health": model["health"],
                "capability_tags": ", ".join(model.get("capability_tags", [])) or "未标记",
                "role": role,
                "basis": basis,
            }
        )
    return assignments


def discussion_prompt(idea: str, role: str, evidence_count: int, reverse_count: int) -> str:
    return textwrap.dedent(
        f"""
        你参与一个由 Codex 主持的机会挖掘讨论。
        想法：{idea}
        你的角色：{role}
        正向证据数：{evidence_count}
        反向证据数：{reverse_count}

        请只输出 3 点：
        1. 你认为最关键的机会判断。
        2. 你最担心的反向风险。
        3. 你建议的 7 天验证动作。
        """
    ).strip()


def invoke_cli_model(model: dict[str, Any], prompt: str, timeout: int) -> str:
    result = subprocess.run(
        model["command"],
        input=prompt,
        text=True,
        shell=True,
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        return f"调用失败：{(result.stderr or result.stdout).strip()[:200]}"
    return result.stdout.strip() or "调用成功但无输出"


def invoke_openai_compatible(model: dict[str, Any], prompt: str, timeout: int) -> str:
    api_key_env = model.get("api_key_env")
    api_key = os.environ.get(api_key_env, "") if api_key_env else ""
    if not api_key:
        return f"未调用：环境变量 {api_key_env or 'API_KEY'} 未设置"

    payload = {
        "model": model["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": int(model.get("max_tokens", 512)),
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        f"{str(model['base_url']).rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BLCaptain-Opportunity-PRD-Skill/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read(200_000).decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return f"调用失败：{str(exc)[:200]}"

    return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip() or "调用成功但无内容"


def run_discussion(
    model_config_path: Path,
    assignments: list[dict[str, str]],
    idea: str,
    evidence_count: int,
    reverse_count: int,
    timeout: int,
    enabled: bool,
) -> list[dict[str, str]]:
    configured_models = {model.get("id"): model for model in load_model_config(model_config_path)}
    traces: list[dict[str, str]] = []
    for assignment in assignments:
        prompt = discussion_prompt(idea, assignment["role"], evidence_count, reverse_count)
        content = "未调用：默认只生成讨论任务；使用 --run-discussion 后才调用模型。"
        if enabled:
            model = configured_models.get(assignment["model_id"], {})
            if assignment["method"] == "cli" and model.get("command"):
                content = invoke_cli_model(model, prompt, timeout)
            elif assignment["method"] == "openai_compatible":
                content = invoke_openai_compatible(model, prompt, timeout)
            elif assignment["method"] == "codex_builtin":
                content = "Codex 主持在当前运行时完成整合，不由脚本重复调用。"
            else:
                content = "未调用：该调用方式暂不支持自动讨论。"
        traces.append({**assignment, "prompt": prompt, "content": content})
    return traces


def to_model_discussion_markdown(mode: str, assignments: list[dict[str, str]], traces: list[dict[str, str]]) -> str:
    lines = [
        "# 动态模型分工与讨论任务",
        "",
        f"- 置信模式：{mode}",
        "- Codex 角色：主持、冲突整合、文件生成、校验和实现交接。",
        "",
        "## 动态模型分工",
        "",
        "| 模型 | 调用方式 | 健康状态 | 能力标签 | 本轮角色 | 分配依据 |",
        "|---|---|---|---|---|---|",
    ]
    if not assignments:
        lines.append("| 无 | 无 | config_required | 无 | 配置引导 | 无可用模型 |")
    for item in assignments:
        lines.append(
            f"| {item['display_name']} | {item['method']} | {item['health']} | {item['capability_tags']} | {item['role']} | {item['basis']} |"
        )

    lines.extend(["", "## 讨论输出", ""])
    for item in traces:
        lines.extend(
            [
                f"### {item['role']} - {item['display_name']}",
                "",
                "任务提示：",
                "",
                "```text",
                item["prompt"],
                "```",
                "",
                "模型输出：",
                "",
                "```text",
                item["content"],
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def estimate_raw_sample_count(sources: list[scan_community_evidence.Source], timeout: int) -> int:
    count = 0
    for source in sources:
        text = scan_community_evidence.read_source(source, timeout)
        count += len(scan_community_evidence.split_blocks(text))
    return count


def infer_intent(idea: str) -> dict[str, str]:
    if "客服" in idea:
        return {
            "target_user": "客服主管、中小商家运营负责人",
            "scene": "每周抽查客服对话、复盘新人、发现服务风险",
            "action": "自动汇总高风险对话并导出质检周报",
            "commercial_goal": "验证是否愿意为节省主管时间和降低漏检付费",
        }
    return {
        "target_user": "待确认",
        "scene": "待确认",
        "action": "待确认",
        "commercial_goal": "验证是否存在可付费痛点",
    }


def methodology_rows(evidence_count: int, commercial_count: int, reverse_count: int) -> list[tuple[str, str, str, str]]:
    rows = [
        ("6W2H", "输入仍是产品想法，需要明确用户、场景、动作、成本。", "先锁定目标用户、使用频次和替代方案。", "P0 只做一个高频动作。"),
        ("NABC", "需要把痛点转成产品感和竞争判断。", "Need 来自手动/表格/截图；Approach 是自动报告；Benefit 是省时；Competition 是现有 QA 套件。", "避免做完整质检平台，优先做轻量报告。"),
    ]
    if commercial_count:
        rows.append(("ROI", "已有付费、太贵、愿意买等商业信号。", "付费锚点应围绕节省主管时间和替代人工抽查。", "7 天实验必须测愿付价格或预约演示。"))
    if reverse_count:
        rows.append(("5Why + 反向压力测试", "存在免费替代、复杂度或隐私等反证。", "先验证为什么现有方案不够，以及哪类客户能绕开阻断。", "P0 要有清晰停止条件。"))
    return rows[:4]


def build_gate_rows(
    mode: str,
    intent: dict[str, str],
    evidence_stats: dict[str, Any],
    reverse_stats: dict[str, Any],
    raw_sample_count: int,
) -> tuple[list[dict[str, str]], str]:
    valid_ratio = evidence_stats["evidence_count"] / raw_sample_count if raw_sample_count else 0
    clear_reverse = reverse_stats["reverse_count"] >= 3 and reverse_stats["high_risk_count"] == 0
    intent_known = sum(1 for value in [intent["target_user"], intent["scene"], intent["commercial_goal"]] if value != "待确认")

    gates = [
        {
            "gate": "G0 多模型配置",
            "result": "通过" if mode != "config_required" else "失败",
            "evidence": f"模型模式：{mode}",
            "action": "继续" if mode != "config_required" else "只输出配置引导",
        },
        {
            "gate": "G1 意图消歧",
            "result": "通过" if intent_known >= 2 else "失败",
            "evidence": f"已明确字段数：{intent_known}",
            "action": "继续" if intent_known >= 2 else "向用户补问目标用户、场景、商业目标",
        },
        {
            "gate": "G2 平台路由",
            "result": "通过" if evidence_stats["platform_count"] >= 3 else "待补",
            "evidence": f"独立平台数：{evidence_stats['platform_count']}",
            "action": "继续" if evidence_stats["platform_count"] >= 3 else "补至少 3 类平台",
        },
        {
            "gate": "G3 证据墙",
            "result": "通过" if evidence_stats["evidence_count"] >= 5 and evidence_stats["platform_count"] >= 2 else "失败",
            "evidence": f"有效证据：{evidence_stats['evidence_count']}，平台：{evidence_stats['platform_count']}",
            "action": "继续" if evidence_stats["evidence_count"] >= 5 else "输出证据不足报告",
        },
        {
            "gate": "G4 数据可信度",
            "result": "通过" if valid_ratio >= 0.3 else "低置信",
            "evidence": f"有效样本/原始样本：{evidence_stats['evidence_count']}/{raw_sample_count or '未知'}",
            "action": "继续" if valid_ratio >= 0.3 else "标注低置信度",
        },
        {
            "gate": "G5 商业信号",
            "result": "通过" if evidence_stats["commercial_signal_count"] >= 1 else "失败",
            "evidence": f"商业信号数：{evidence_stats['commercial_signal_count']}",
            "action": "继续" if evidence_stats["commercial_signal_count"] >= 1 else "输出 Watch",
        },
        {
            "gate": "G6 反向证据",
            "result": "通过" if clear_reverse else "失败",
            "evidence": f"反向证据：{reverse_stats['reverse_count']}，高风险：{reverse_stats['high_risk_count']}",
            "action": "继续" if clear_reverse else "Pivot 或 No-Go，先回应反证",
        },
        {
            "gate": "G7 MVP 可验证",
            "result": "通过" if evidence_stats["evidence_count"] >= 5 else "待补",
            "evidence": "可用社区原话招募 7 天访谈和落地页验证" if evidence_stats["evidence_count"] >= 5 else "测试用户来源不足",
            "action": "继续" if evidence_stats["evidence_count"] >= 5 else "收窄切口",
        },
        {
            "gate": "G8 PRD 可交接",
            "result": "待生成",
            "evidence": "Go 后由 PRD 校验脚本确认 P0 evidence_id 和验收剧本",
            "action": "Go 后生成并校验 PRD",
        },
    ]

    if mode == "config_required" or intent_known < 2 or evidence_stats["evidence_count"] < 3:
        decision = "No-Go"
    elif evidence_stats["evidence_count"] < 5 or valid_ratio < 0.3 or evidence_stats["commercial_signal_count"] == 0:
        decision = "Watch"
    elif not clear_reverse:
        decision = "Pivot"
    else:
        decision = "Go"
        gates[-1]["result"] = "通过"
        gates[-1]["evidence"] = "P0 功能将绑定 evidence_id，验收剧本不少于 3 条"
        gates[-1]["action"] = "生成商业化机会 PRD"
    return gates, decision


def gate_confidence(decision: str, mode: str) -> str:
    if decision != "Go":
        return "中" if mode != "config_required" else "低"
    return "中" if mode == "low_confidence" else "高"


def build_assessment(
    idea: str,
    mode: str,
    intent: dict[str, str],
    evidence: list[dict[str, str]],
    evidence_stats: dict[str, Any],
    reverse_items: list[dict[str, str]],
    reverse_stats: dict[str, Any],
    gates: list[dict[str, str]],
    decision: str,
) -> str:
    confidence = gate_confidence(decision, mode)
    next_step = "生成商业化机会 PRD 并进入 7 天实验" if decision == "Go" else "不生成商业化机会 PRD，先补证或调整切口"
    reason = {
        "Go": "正向证据、商业信号和可回应反证达到 Gate 阈值。",
        "Watch": "痛点存在，但证据强度、商业信号或可信度不足。",
        "Pivot": "正向证据存在，但反向证据提示原切口需要调整。",
        "No-Go": "关键 Gate 未通过，继续生成 PRD 会放大脑补风险。",
    }[decision]

    lines = [
        "# 机会评估报告",
        "",
        "## 决策",
        "",
        "| 字段 | 内容 |",
        "|---|---|",
        f"| 结论 | {decision} |",
        f"| 置信度 | {confidence} |",
        f"| 一句话理由 | {reason} |",
        f"| 下一步 | {next_step} |",
        "",
        "## 意图卡",
        "",
        "| 字段 | 内容 |",
        "|---|---|",
        f"| 想法 | {idea} |",
        f"| 目标用户 | {intent['target_user']} |",
        f"| 场景 | {intent['scene']} |",
        f"| 核心动作 | {intent['action']} |",
        f"| 商业目标 | {intent['commercial_goal']} |",
        "",
        "## 正向证据摘要",
        "",
        "| evidence_id | 关键原话 | 支持的痛点 | 支持的商业假设 |",
        "|---|---|---|---|",
    ]
    for item in evidence[:6]:
        lines.append(
            f"| {item['evidence_id']} | {item['quote']} | {item['behavior_signal']} | {item['commercial_signal']} |"
        )

    lines.extend(["", "## 反向证据摘要", "", "| reverse_id | 反向问题 | 回应 | 剩余风险 |", "|---|---|---|---|"])
    for item in reverse_items[:5]:
        lines.append(f"| {item['reverse_id']} | {item['labels']} | {item['response']} | {item['conclusion']} |")

    lines.extend(["", "## 方法论选择", "", "| 方法 | 触发原因 | 关键结论 | 对 MVP 的影响 |", "|---|---|---|---|"])
    for method, trigger, conclusion, impact in methodology_rows(
        evidence_stats["evidence_count"], evidence_stats["commercial_signal_count"], reverse_stats["reverse_count"]
    ):
        lines.append(f"| {method} | {trigger} | {conclusion} | {impact} |")

    lines.extend(["", "## Gate 结果", "", "| Gate | 结果 | 证据 | 处理 |", "|---|---|---|---|"])
    for gate in gates:
        lines.append(f"| {gate['gate']} | {gate['result']} | {gate['evidence']} | {gate['action']} |")

    lines.extend(
        [
            "",
            "## 7 天关键假设实验",
            "",
            "| 假设 | 实验动作 | 通过标准 | 停止标准 |",
            "|---|---|---|---|",
            "| 目标用户愿意为轻量客服质检周报付费 | 用 5 条证据原话做落地页和 5 个访谈邀约 | 7 天内获得 3 个明确试用或付费意向 | 少于 1 个明确意向，或主要反对点集中在预算/隐私 |",
            "| 默认周报比完整平台更容易采用 | 做 1 个可点击样例报告或人工代跑报告 | 3 个用户愿意提供样本数据试跑 | 用户坚持需要完整集成或无法提供数据 |",
            "",
            "## 停止或补证条件",
            "",
            f"- 证据不足：有效证据数 {evidence_stats['evidence_count']}，低于 Gate 时停止。",
            f"- 商业信号不足：商业信号数 {evidence_stats['commercial_signal_count']}，为 0 时不生成商业化机会 PRD。",
            f"- 反向证据无法回应：高风险反证数 {reverse_stats['high_risk_count']}，大于 0 时先 Pivot。",
        ]
    )
    if decision != "Go":
        lines.append("- 当前结论：不生成商业化机会 PRD。")
    return "\n".join(lines)


def build_commercial_prd(
    idea: str,
    intent: dict[str, str],
    evidence: list[dict[str, str]],
    reverse_items: list[dict[str, str]],
    gates: list[dict[str, str]],
) -> str:
    p0_evidence = evidence[:3]
    evidence_refs = ", ".join(item["evidence_id"] for item in evidence[:5])

    def source_ref(item: dict[str, str]) -> str:
        if item["url"].startswith("http"):
            return item["url"]
        return f"{item['url']}#{item['evidence_id']}"

    lines = [
        "# 商业化机会 + 工程实施 PRD",
        "",
        "## 0. 商业速读卡",
        "",
        "| 字段 | 内容 |",
        "|---|---|",
        f"| 产品一句话 | {idea}：为{intent['target_user']}自动生成轻量客服质检周报 |",
        f"| 目标用户 | {intent['target_user']} |",
        f"| 核心痛点 | 手动抽查、截图复盘、表格整理费时且漏检 |",
        f"| 商业信号 | 付费、太贵、愿意买、cheap export 等信号来自 {evidence_refs} |",
        "| P0 | 导入对话样本 -> 自动标注风险 -> 导出周报 |",
        "| 7 天实验 | 5 个客服主管访谈 + 1 个样例周报 + 3 个试跑承诺 |",
        "| 工程交付形态 | Web 控制台 + API 服务 + 分析 Worker + 风险标注引擎 + 报告导出 |",
        "| 成本上限 | P0 单批 1000 条对话内完成分析，单批 LLM 成本上限 3 元，超出时降级为规则优先和抽样分析 |",
        "",
        "## 1. 机会摘要",
        "",
        "结论：Go。",
        "",
        "当前机会来自近 30 天多社区评论。用户不是泛泛说想要 AI，而是在客服复盘中反复提到手动、截图、表格、半天、太慢和付费意愿。本 PRD 的定位是先交付一个可验证、可回滚、可人工复核的 P0 工程版本，不扩展为完整客服系统。",
        "",
        "## 2. 证据墙",
        "",
        "| evidence_id | 平台 | 日期 | URL | 用户原话 | 行为信号 | 商业信号 |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in evidence:
        lines.append(
            f"| {item['evidence_id']} | {item['platform']} | {item['date']} | {source_ref(item)} | {item['quote']} | {item['behavior_signal']} | {item['commercial_signal']} |"
        )

    lines.extend(
        [
            "",
            "## 3. 目标用户与核心 JTBD",
            "",
            f"- 目标用户：{intent['target_user']}。",
            f"- 场景：{intent['scene']}。",
            "- JTBD：当一周客服对话积累后，用户想快速知道哪些对话值得复盘，以便训练新人、发现风险并减少漏检。",
            "",
            "## 4. 当前替代方案与竞品缺口",
            "",
            "- 当前替代：人工抽查、截图、表格、现有客服系统内置报表、完整 QA 套件。",
            "- 缺口：完整 QA 套件太重或太贵，内置报表只覆盖基础统计，轻量团队需要默认周报和可追溯证据。",
            "",
            "## 5. 需求分析与方法论选择",
            "",
            "| 方法 | 结论 |",
            "|---|---|",
            "| NABC | Need 是节省主管抽查时间；Approach 是默认周报；Benefit 是省时和减少漏检；Competition 是内置报表和完整 QA 套件。 |",
            "| ROI | 用节省主管时间和减少新人复盘成本做付费锚点。 |",
            "| KANO | P0 只做导入、标注、导出；集成、多角色权限和复杂质检规则放弃。 |",
            "",
            "## 6. MVP 功能边界",
            "",
            "| 用户故事 | evidence_id | 验收标准 | 不做什么 |",
            "|---|---|---|---|",
        ]
    )
    stories = [
        ("作为客服主管，我想导入一批客服对话，以便不用手动复制到表格。", "上传或粘贴样本后 30 秒内生成处理结果。", "不做多系统实时同步。"),
        ("作为客服主管，我想看到高风险对话列表，以便优先复盘新人和差评风险。", "每条风险都能显示原话片段和风险原因。", "不做复杂自定义规则引擎。"),
        ("作为运营负责人，我想导出周报，以便向团队复盘和判断是否值得继续付费。", "一键导出 Markdown/CSV 周报，包含风险计数和原话引用。", "不做完整 BI 看板。"),
    ]
    for story, item in zip(stories, p0_evidence):
        story_text, acceptance, excluded = story
        lines.append(f"| {story_text} | {item['evidence_id']} | {acceptance} | {excluded} |")

    lines.extend(
        [
            "",
            "## 7. 商业模型与增长路径",
            "",
            "- 商业模型：按团队订阅，先测试低价轻量版，再验证更高价的审计留痕和团队协作。",
            "- 付费锚点：节省主管抽查时间、减少新人复盘成本、降低漏检风险。",
            "- 增长路径：从客服主管访谈、Product Hunt 竞品评论、Reddit smallbusiness、小红书商家评论中招募试跑用户。",
            "",
            "## 8. 产品交互与核心流程",
            "",
            "1. 用户导入客服对话样本。",
            "2. 系统自动识别风险对话、重复问题和训练建议。",
            "3. 用户查看默认周报并导出给团队。",
            "",
            "## 9. 工程实施方案",
            "",
            "### 9.1 系统架构",
            "",
            "| 模块 | 职责 | 输入 | 输出 | P0 边界 |",
            "|---|---|---|---|---|",
            "| Web 控制台 | 导入样本、展示任务状态、查看和导出周报 | CSV、粘贴文本、用户操作 | 导入结果、报告页、导出文件 | 不做多租户后台和复杂 BI 看板 |",
            "| API 服务 | 鉴权、导入任务、报告查询、删除请求 | HTTP 请求 | JSON 响应、错误码 | P0 只支持单团队空间 |",
            "| Import Parser | 解析 CSV 或粘贴文本，生成 Conversation | 原始文件或文本 | Conversation 记录、解析错误 | 不接实时客服系统 |",
            "| Analysis Worker | 执行规则和 LLM 分析，写入 RiskFinding | Conversation 批次 | 风险标注、置信度、证据片段 | 单批最多 1000 条对话 |",
            "| Risk Engine | 规则优先识别服务态度、响应慢、未解决、升级风险 | 对话文本、规则配置 | risk_type、severity、confidence | 不做用户自定义规则引擎 |",
            "| Report Exporter | 汇总 WeeklyReport 并导出 Markdown/CSV | RiskFinding、统计指标 | report.md、report.csv | 不做 PDF 和在线协作批注 |",
            "| Metadata DB | 保存任务、报告、审计日志和删除状态 | API/Worker 写入 | 可查询元数据 | 原始敏感文本默认 7 天删除 |",
            "",
            "### 9.2 数据流",
            "",
            "1. 用户上传脱敏 CSV 或粘贴对话文本，API 创建 ImportBatch。",
            "2. Import Parser 校验格式、抽取 Conversation，并记录解析状态。",
            "3. Analysis Worker 先跑规则标注，再对规则无法判断的样本调用 LLM fallback。",
            "4. Risk Engine 写入 RiskFinding，包含 risk_type、severity、confidence、evidence_excerpt 和 rationale。",
            "5. Report Exporter 汇总 WeeklyReport，生成风险分布、重点对话、训练建议和导出文件。",
            "6. 用户下载 Markdown/CSV，或发起删除，系统记录 AuditLog 并按删除策略清理原始文本。",
            "",
            "### 9.3 技术选型",
            "",
            "| 层级 | P0 选择 | 理由 | 暂不采用 |",
            "|---|---|---|---|",
            "| 前端 | 简单 Web 控制台 | 导入、状态、报告查看足够验证价值 | 移动 App、复杂仪表盘 |",
            "| 后端 | HTTP API + 后台 Worker | 分离导入和分析，便于超时重试 | 微服务拆分 |",
            "| 存储 | 元数据表 + 临时对象存储 | 满足报告追溯和删除策略 | 长期保存全量聊天记录 |",
            "| AI 分析 | 规则优先 + LLM fallback | 控制成本并保留可解释性 | 全量 LLM 逐条分析 |",
            "| 导出 | Markdown 和 CSV | 满足团队复盘和二次整理 | PDF、PPT、在线协作 |",
            "",
            "### 9.4 AI 风险标注方案",
            "",
            "| 项 | 内容 |",
            "|---|---|",
            "| 标签体系 | response_delay、unresolved_issue、negative_tone、refund_or_complaint、training_example |",
            "| 规则优先级 | 明确关键词、等待时长、重复追问和差评词先由规则识别 |",
            "| LLM fallback | 仅处理规则未命中或冲突样本，要求返回 JSON：risk_type、severity、confidence、evidence_excerpt、rationale |",
            "| 置信度 | confidence 低于 0.7 标为 low_confidence，不进入自动结论，只进入人工复核队列 |",
            "| 低置信度处理 | 报告中单独展示低置信度样本，不计入高风险统计 |",
            "| 人工复核 | 用户可把 RiskFinding 标记为 confirmed、dismissed、needs_followup |",
            "| 成本上限 | 单批 LLM 成本上限 3 元；达到上限后停止 LLM fallback，并提示使用抽样分析 |",
            "",
            "## 10. 数据模型与字段字典",
            "",
            "| 实体 | 字段 | 类型 | 来源 | 是否必填 | 保留策略 | 说明 |",
            "|---|---|---|---|---|---|---|",
            "| ImportBatch | import_id | string | 系统生成 | 是 | 长期保留元数据 | 导入批次 ID |",
            "| ImportBatch | tenant_id | string | 当前团队 | 是 | 长期保留元数据 | P0 可用单团队默认值 |",
            "| ImportBatch | status | enum | 系统状态 | 是 | 长期保留元数据 | pending、parsed、analyzing、completed、failed、deleted |",
            "| Conversation | conversation_id | string | 系统生成 | 是 | 原始文本默认 7 天删除 | 单条对话 ID |",
            "| Conversation | customer_text | text | 用户上传 | 是 | 默认 7 天删除 | 客户消息，入库前执行脱敏 |",
            "| Conversation | agent_text | text | 用户上传 | 否 | 默认 7 天删除 | 客服回复，入库前执行脱敏 |",
            "| Conversation | occurred_at | datetime | 用户上传或解析 | 否 | 默认 7 天删除 | 对话发生时间 |",
            "| RiskFinding | finding_id | string | 系统生成 | 是 | 随报告保留 30 天 | 风险记录 ID |",
            "| RiskFinding | risk_type | enum | 规则或 LLM | 是 | 随报告保留 30 天 | 风险标签 |",
            "| RiskFinding | severity | enum | 规则或 LLM | 是 | 随报告保留 30 天 | low、medium、high |",
            "| RiskFinding | confidence | number | 规则或 LLM | 是 | 随报告保留 30 天 | 0 到 1 |",
            "| RiskFinding | evidence_excerpt | text | 对话片段 | 是 | 随报告保留 30 天 | 必须可追溯到原话 |",
            "| WeeklyReport | report_id | string | 系统生成 | 是 | 30 天后可删除 | 周报 ID |",
            "| WeeklyReport | export_format | enum | 用户选择 | 是 | 30 天后可删除 | markdown、csv |",
            "| AuditLog | action | enum | 系统记录 | 是 | 180 天 | import、analyze、export、delete |",
            "",
            "## 11. API 契约",
            "",
            "| 接口 | 方法 | 请求字段 | 响应字段 | 错误码 | 权限 |",
            "|---|---|---|---|---|---|",
            "| /api/imports | POST | file 或 raw_text、channel、timezone | import_id、status、parsed_count、errors | INVALID_FILE_FORMAT、FILE_TOO_LARGE、EMPTY_CONVERSATION | workspace_member |",
            "| /api/imports/{import_id} | GET | import_id | status、parsed_count、failed_count、created_at | IMPORT_NOT_FOUND | workspace_member |",
            "| /api/analysis-jobs | POST | import_id、analysis_mode | job_id、status、cost_estimate | IMPORT_NOT_READY、COST_LIMIT_EXCEEDED | workspace_member |",
            "| /api/reports/{report_id} | GET | report_id | summary、risk_findings、metrics、low_confidence_items | REPORT_NOT_FOUND、DATA_RETENTION_EXPIRED | workspace_member |",
            "| /api/reports/{report_id}/export | GET | format=markdown 或 csv | download_url、expires_at | EXPORT_FAILED、UNSUPPORTED_FORMAT | workspace_member |",
            "| /api/imports/{import_id} | DELETE | import_id、delete_raw=true | status、deleted_at | DELETE_LOCKED、IMPORT_NOT_FOUND | workspace_admin |",
            "",
            "## 12. 权限、安全、隐私与合规",
            "",
            "| 主题 | P0 要求 | 验收方式 |",
            "|---|---|---|",
            "| 权限 | workspace_member 可导入和查看报告，workspace_admin 可删除批次 | 用两类账号调用 API 验证 403 和成功路径 |",
            "| 脱敏 | 默认识别手机号、邮箱、订单号并在报告中遮罩 | 上传含敏感字段样本，检查导出文件不含原始敏感值 |",
            "| 删除策略 | 原始对话默认 7 天删除，报告和风险摘要默认 30 天删除 | 创建过期样本，触发清理任务并检查状态为 deleted |",
            "| 审计日志 | import、analyze、export、delete 均写 AuditLog | 每条核心操作可查 action、actor、target_id、created_at |",
            "| 数据隔离 | tenant_id 必须参与所有查询条件 | 跨 tenant 查询返回 403 或空结果 |",
            "| 合规边界 | P0 不接生产客服系统，不长期保存未脱敏原文 | PRD、界面提示和导入页均显示数据处理说明 |",
            "",
            "## 13. 非功能需求",
            "",
            "| 类型 | 指标 | 验收方式 |",
            "|---|---|---|",
            "| 性能 | 20 条对话 30 秒内完成报告；1000 条对话 10 分钟内完成 | 运行固定样本压测并记录耗时 |",
            "| 容量 | P0 单文件最大 10MB，单批最多 1000 条 Conversation | 上传边界文件，检查限制和提示 |",
            "| 可用性 | 分析任务失败可重试，导入失败不丢失错误明细 | 模拟 Worker 超时和重试 |",
            "| 成本 | 单批 LLM 成本上限 3 元，超限自动降级 | mock 成本计数器触发降级 |",
            "| 数据保留 | 原始文本 7 天，报告 30 天，AuditLog 180 天 | 检查清理任务和删除状态 |",
            "",
            "## 14. 异常流程和边界条件",
            "",
            "| 场景 | 系统行为 | 用户提示 | 记录/告警 |",
            "|---|---|---|---|",
            "| 导入格式错误 | 拒绝入库并返回行号 | 文件格式不支持，请使用 CSV 或粘贴文本 | 记录 INVALID_FILE_FORMAT |",
            "| 空数据 | 不创建分析任务 | 未识别到有效对话 | 记录 EMPTY_CONVERSATION |",
            "| 低置信度过多 | 报告标记需人工复核，不给自动结论 | 部分样本置信度不足，请人工确认 | 记录 LOW_CONFIDENCE_RESULT |",
            "| 分析超时 | Worker 停止当前批次，可重试 | 分析超时，请减少样本或重试 | 记录 ANALYSIS_TIMEOUT 并告警 |",
            "| 导出失败 | 保留报告状态，可重新导出 | 导出失败，请稍后重试 | 记录 EXPORT_FAILED |",
            "| 数据过期 | 不返回原始片段，只返回摘要 | 原始数据已按删除策略清理 | 记录 DATA_RETENTION_EXPIRED |",
            "",
            "## 15. 测试方案和验收标准",
            "",
            "| 测试类型 | 覆盖范围 | 通过标准 |",
            "|---|---|---|",
            "| 单元测试 | CSV 解析、脱敏、规则标签、成本计数、删除策略 | 核心函数分支覆盖主要边界 |",
            "| 集成测试 | 导入 -> 分析 -> 报告 -> 导出 -> 删除 | 固定样本链路全通过 |",
            "| 端到端验收 | 3 条验收剧本 | 用户操作路径无阻断 |",
            "| 人工评估 | 30 条人工标注样本 | 高风险召回可解释，低置信度样本进入复核 |",
            "| 安全测试 | 权限、跨 tenant、敏感字段导出 | 未授权访问失败，导出不泄露敏感字段 |",
            "",
            "## 16. 部署运维与监控",
            "",
            "| 项 | P0 要求 |",
            "|---|---|",
            "| 部署方式 | 单体 API 服务 + Worker 进程 + 元数据库 + 临时对象存储 |",
            "| 配置项 | MODEL_PROVIDER、MODEL_API_KEY_ENV、LLM_COST_LIMIT、RAW_DATA_RETENTION_DAYS、REPORT_RETENTION_DAYS |",
            "| 日志 | request_id、tenant_id、import_id、job_id、error_code，不记录完整原文 |",
            "| 监控指标 | import_success_rate、analysis_duration、llm_cost_per_batch、low_confidence_rate、export_success_rate |",
            "| 告警 | 分析失败率超过 10%、导出失败率超过 5%、成本上限频繁触发 |",
            "| 回滚 | 保留上一版规则配置；模型提示词版本化；导出格式变更必须兼容旧报告 |",
            "",
            "## 17. 埋点与验证指标",
            "",
            "| 事件 | 触发时机 | 属性 | 用途 |",
            "|---|---|---|---|",
            "| import_started | 用户提交样本 | source_type、file_size、tenant_id | 判断导入意愿 |",
            "| import_completed | 解析完成 | parsed_count、failed_count | 判断样本质量 |",
            "| report_generated | 周报生成 | risk_count、low_confidence_count、duration | 判断核心价值 |",
            "| export_clicked | 用户导出 | format、report_id | 判断报告是否可用 |",
            "| finding_reviewed | 用户确认或驳回风险 | risk_type、reviewer_status | 改进风险标签 |",
            "| delete_requested | 用户删除数据 | import_id、raw_deleted | 验证隐私信任 |",
            "",
            "## 18. 开发任务拆分与 DoD",
            "",
            "| 任务 | 输入 | 输出 | DoD |",
            "|---|---|---|---|",
            "| T1 导入与解析 | CSV 或粘贴文本 | ImportBatch、Conversation、解析错误 | 10MB 文件限制、空数据、格式错误测试通过 |",
            "| T2 脱敏和删除策略 | Conversation 原文 | 脱敏文本、删除状态、AuditLog | 敏感字段不出现在导出文件，7 天删除任务可验证 |",
            "| T3 风险标注引擎 | Conversation 批次 | RiskFinding、confidence、rationale | 规则命中、LLM fallback、低置信度分支均有测试 |",
            "| T4 报告生成和导出 | RiskFinding、统计指标 | WeeklyReport、Markdown/CSV | 3 条验收剧本全部通过 |",
            "| T5 API 和权限 | API 契约 | 可调用接口、错误码、403 | 表格中的 API 契约均有集成测试 |",
            "| T6 监控和成本控制 | Worker 日志、成本计数 | 指标、告警、降级提示 | 成本上限和分析超时可被模拟触发 |",
            "",
            "## 19. 7 天验证计划",
            "",
            "| 假设 | 实验动作 | 通过标准 | 停止标准 |",
            "|---|---|---|---|",
            "| 轻量周报足够替代手动抽查 | 人工代跑 5 份样例周报 | 3 个用户愿意继续试用 | 用户必须要完整系统集成 |",
            "| 用户愿意为省时付费 | 提供 2 档价格并询问预付或预约 | 2 个用户接受付费或试点 | 用户只接受免费方案 |",
            "| 隐私风险可控 | 提供脱敏样本和本地删除说明 | 3 个用户愿意提供脱敏样本 | 用户无法提供任何数据 |",
            "",
            "## 20. 风险、反证与停止条件",
            "",
            "| reverse_id | 风险 | 回应 | 停止条件 |",
            "|---|---|---|---|",
        ]
    )
    for item in reverse_items:
        lines.append(f"| {item['reverse_id']} | {item['labels']} | {item['response']} | {item['conclusion']} 持续扩大且无法回应 |")

    lines.extend(
        [
            "",
            "## 21. AI 开发者交接说明",
            "",
            "- 先做 T1、T2、T3：样本导入、脱敏删除、风险标注引擎；再做 T4 报告导出。",
            "- 不能重解释的事实：所有 P0 都必须绑定 evidence_id，所有风险都必须绑定 reverse_id。",
            "- 可自由优化：报告排版、风险标签名称、CSV 字段顺序、规则关键词。",
            "- 未知项：真实数据接入方式、可接受价格、隐私部署要求。",
            "- 第一版验证：使用 5 份脱敏客服对话样本，输出周报并回访用户是否愿意继续使用。",
            "- 推荐第一批文件：导入解析模块、风险标注模块、报告导出模块、API 路由、数据清理任务、校验测试。",
            "- 不允许扩展：实时客服系统集成、复杂权限后台、完整 BI、PDF/PPT 导出、绩效考核系统。",
            "- 生成代码前必须确认：API 契约、字段字典、错误码、删除策略、成本上限和验收剧本没有缺口。",
            "",
            "## Gate 结果",
            "",
            "| Gate | 结果 | 证据 | 处理 |",
            "|---|---|---|---|",
        ]
    )
    for gate in gates:
        lines.append(f"| {gate['gate']} | {gate['result']} | {gate['evidence']} | {gate['action']} |")

    lines.extend(
        [
            "",
            "## 验收剧本",
            "",
            f"1. 上传 20 条脱敏客服对话后，系统生成周报，并能追溯到 {p0_evidence[0]['evidence_id']} 的手动整理痛点。",
            f"2. 周报中每条风险都显示原话片段和风险原因，并能追溯到 {p0_evidence[1]['evidence_id']} 的截图复盘痛点。",
            f"3. 导出 Markdown/CSV 后，用户能直接用于团队复盘，并能追溯到 {p0_evidence[2]['evidence_id']} 的表格整理痛点。",
        ]
    )
    return "\n".join(lines)


def validate_generated_prd(path: Path) -> tuple[bool, list[str]]:
    errors = validate_opportunity_prd.lint_file(path)
    return not errors, errors


def run_workflow(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_config_path = Path(args.model_config)
    sources_path = Path(args.sources)
    reverse_sources_path = Path(args.reverse_sources or args.sources)

    health_results, health_markdown = model_health(model_config_path, args.timeout)
    mode = check_model_pool.decide_mode(health_results)
    write_text(output_dir / "model-health.md", health_markdown)
    write_json(output_dir / "model-health.json", {"mode": mode, "models": health_results})

    forward_sources = scan_community_evidence.parse_sources(sources_path)
    evidence = scan_community_evidence.scan_sources(forward_sources, args.timeout)
    evidence_payload = scan_community_evidence.to_payload(args.idea, forward_sources, evidence)
    write_text(output_dir / "evidence-report.md", scan_community_evidence.to_markdown(args.idea, forward_sources, evidence))
    write_json(output_dir / "evidence-report.json", evidence_payload)
    scan_community_evidence.write_csv(
        str(output_dir / "evidence-report.csv"),
        evidence,
        ["evidence_id", "platform", "date", "url", "quote", "behavior_signal", "commercial_signal", "level"],
    )

    reverse_sources = scan_reverse_evidence.parse_sources(reverse_sources_path)
    reverse_items = scan_reverse_evidence.scan_sources(reverse_sources, args.timeout)
    reverse_payload = scan_reverse_evidence.to_payload(args.idea, reverse_sources, reverse_items)
    write_text(output_dir / "reverse-evidence-report.md", scan_reverse_evidence.to_markdown(args.idea, reverse_sources, reverse_items))
    write_json(output_dir / "reverse-evidence-report.json", reverse_payload)
    scan_reverse_evidence.write_csv(
        str(output_dir / "reverse-evidence-report.csv"),
        reverse_items,
        ["reverse_id", "source", "date", "url", "reverse_evidence", "impact", "response", "conclusion", "risk", "labels"],
    )

    assignments = assign_roles(health_results)
    traces = run_discussion(
        model_config_path,
        assignments,
        args.idea,
        evidence_payload["stats"]["evidence_count"],
        reverse_payload["stats"]["reverse_count"],
        args.timeout,
        args.run_discussion,
    )
    write_text(output_dir / "model-discussion.md", to_model_discussion_markdown(mode, assignments, traces))
    write_json(output_dir / "model-discussion.json", {"mode": mode, "assignments": assignments, "traces": traces})

    raw_sample_count = estimate_raw_sample_count(forward_sources, args.timeout)
    intent = infer_intent(args.idea)
    gates, decision = build_gate_rows(mode, intent, evidence_payload["stats"], reverse_payload["stats"], raw_sample_count)
    assessment = build_assessment(
        args.idea,
        mode,
        intent,
        evidence,
        evidence_payload["stats"],
        reverse_items,
        reverse_payload["stats"],
        gates,
        decision,
    )
    assessment_path = output_dir / "opportunity-assessment.md"
    write_text(assessment_path, assessment)

    prd_path = output_dir / "commercial-opportunity-prd.md"
    prd_valid = False
    prd_errors: list[str] = []
    if decision == "Go":
        prd = build_commercial_prd(args.idea, intent, evidence, reverse_items, gates)
        write_text(prd_path, prd)
        prd_valid, prd_errors = validate_generated_prd(prd_path)

    summary = {
        "idea": args.idea,
        "decision": decision,
        "mode": mode,
        "output_dir": display_path(output_dir),
        "evidence_count": evidence_payload["stats"]["evidence_count"],
        "reverse_count": reverse_payload["stats"]["reverse_count"],
        "commercial_signal_count": evidence_payload["stats"]["commercial_signal_count"],
        "prd_generated": decision == "Go",
        "prd_valid": prd_valid,
        "prd_errors": prd_errors,
    }
    write_json(output_dir / "workflow-summary.json", summary)
    write_text(output_dir / "workflow-summary.md", to_summary_markdown(summary, gates))
    return summary


def to_summary_markdown(summary: dict[str, Any], gates: list[dict[str, str]]) -> str:
    lines = [
        "# 机会挖掘工作流总结",
        "",
        f"- 想法：{summary['idea']}",
        f"- 决策：{summary['decision']}",
        f"- 模型模式：{summary['mode']}",
        f"- 输出目录：{summary['output_dir']}",
        f"- 正向证据数：{summary['evidence_count']}",
        f"- 反向证据数：{summary['reverse_count']}",
        f"- 商业信号数：{summary['commercial_signal_count']}",
        f"- 是否生成 PRD：{'是' if summary['prd_generated'] else '否'}",
        f"- PRD 校验：{'通过' if summary['prd_valid'] else '未通过或未生成'}",
        "",
        "## Gate 摘要",
        "",
        "| Gate | 结果 | 处理 |",
        "|---|---|---|",
    ]
    for gate in gates:
        lines.append(f"| {gate['gate']} | {gate['result']} | {gate['action']} |")
    if summary["prd_errors"]:
        lines.extend(["", "## PRD 校验错误", ""])
        lines.extend(f"- {error}" for error in summary["prd_errors"])
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run the full opportunity discovery to PRD workflow.")
    parser.add_argument("--idea", required=True, help="Product idea or opportunity hypothesis.")
    parser.add_argument("--model-config", default=str(DEFAULT_MODEL_CONFIG), help="Model pool JSON config.")
    parser.add_argument("--sources", default=str(DEFAULT_SOURCES), help="Positive evidence sources JSON.")
    parser.add_argument("--reverse-sources", help="Reverse evidence sources JSON. Defaults to --sources.")
    parser.add_argument("--output-dir", default=str(RUN_DIR), help="Directory for generated workflow artifacts.")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--run-discussion", action="store_true", help="Actually invoke callable models for discussion.")
    args = parser.parse_args(argv)

    start = time.time()
    summary = run_workflow(args)
    elapsed_ms = int((time.time() - start) * 1000)
    print(f"工作流完成：{summary['decision']}，输出目录：{summary['output_dir']}，耗时：{elapsed_ms}ms")
    if summary["prd_generated"] and not summary["prd_valid"]:
        print("PRD 已生成但校验失败：")
        for error in summary["prd_errors"]:
            print(f"- {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
