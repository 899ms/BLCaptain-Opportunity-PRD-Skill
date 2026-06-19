# BLCaptain Opportunity PRD Skill

> Turn a product idea into an evidence-backed opportunity assessment and, only when the Gates pass, an engineering-ready commercial PRD.

[中文 README](README.md)

![Python](https://img.shields.io/badge/Python-%3E%3D3.10-2b2622.svg)
![Agent Skill](https://img.shields.io/badge/Agent-Skill-d98e3a.svg)
![Evidence Based](https://img.shields.io/badge/PRD-Evidence--Based-2f5ea7.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## What It Does

BLCaptain Opportunity PRD Skill helps an agent move from a rough product idea or a batch of community comments to a traceable opportunity decision:

- collect evidence from community comments, product reviews, issues, Q&A, forums, and user-provided exports;
- extract user quotes, dates, sources, behavior signals, commercial signals, and reverse evidence;
- run business Gates before writing product requirements;
- output Go / Watch / Pivot / No-Go decisions;
- generate a commercial and engineering PRD only when the evidence supports Go.

It is not an idea generator. It is an evidence and business validation workflow. No evidence means no validated requirement. No commercial signal means no commercial PRD. No engineering contract means no handoff to development.

## Core Capabilities

| Area | Capability |
|---|---|
| Input | One-line idea, product direction, competitor, public URL, comment export, local sample |
| Evidence | User quote, date, source, URL or file, behavior signal, commercial signal, reverse evidence |
| Analysis | Intent card, platform routing, evidence wall, reverse-evidence wall, methodology routing, business Gates |
| Decision | Go / Watch / Pivot / No-Go |
| Output | Opportunity assessment first; commercial and engineering PRD only after Go |
| Engineering PRD | Architecture, data flow, API contract, field dictionary, errors, privacy, tests, deployment, monitoring, DoD |

## Multi-Model Workflow

Users configure their own available models or local model commands. The Skill checks model health first, then assigns roles dynamically.

- No usable external model: output only a configuration guide.
- One usable external model: run in low-confidence single-model mode.
- Multiple usable external models: assign analysis, reverse review, structure, external view, or implementation roles based on actual capability tags.

The workflow is always hosted by Codex or the current coding agent. Codex is the host, final synthesizer, file writer, and validator, but it does not count as an external model. The Skill does not hard-code fixed duties for any specific model brand.

## Supported Models and Configuration

This Skill is provider-neutral. Any model that can return text through an OpenAI-compatible API or a local CLI command can be connected.

| Model / Type | Recommended Method | Typical Role |
|---|---|---|
| DeepSeek | `openai_compatible` or `cli` | commercial opposition, cost-benefit review, structured critique |
| GLM | `openai_compatible` or `cli` | Chinese context, long comments, methodology structure |
| Claude / Claude Code | `cli` first | long-context reading, reverse stress test, synthesis review |
| Gemini | `openai_compatible` or `cli` | external trends, multimodal clues, general analysis |
| Grok | `openai_compatible` or `cli` | social perspective, live discussion, contrary signals |
| Local models, such as Ollama or local scripts | `cli` | low-cost triage, code or structure assistance |
| Other compatible models | `openai_compatible` or `cli` | dynamically assigned by capability tags |

Configuration files:

- `templates/model-pool.example.json`: empty default model pool for new users; no mock model is included.
- `templates/model-pool.providers.example.json`: copyable examples for DeepSeek, GLM, Claude CLI, Gemini, Grok, and local models.

The simplest path is to ask Codex to configure the model for you after installation:

```text
Use BLCaptain Opportunity PRD Skill to connect DeepSeek.
I have an API key, and I want the environment variable name to be DEEPSEEK_API_KEY.
```

Or:

```text
Use BLCaptain Opportunity PRD Skill to connect Claude CLI.
My local non-interactive command is: claude -p
```

Codex should then:

1. Decide whether the model should use `openai_compatible` or `cli`.
2. Create or update a local model config file.
3. Remind you not to put real API keys in JSON.
4. Explain how to store secrets in environment variables, Keychain, 1Password, Bitwarden, a private local dotenv file, or the model CLI login state.
5. Run the health check and explain whether the status is `config_required`, `low_confidence`, `standard`, or `heavy_discussion`.

If you prefer manual setup:

1. Create a local model config, for example `my-model-pool.json`.
2. Copy the model entries you need from `templates/model-pool.providers.example.json`.
3. Fill only `base_url`, `model`, `api_key_env`, or `command`.
4. Store real secrets in environment variables, macOS Keychain, 1Password, Bitwarden, a private local dotenv file, or the model CLI login state.
5. Run the health check and confirm at least one external model is usable.

OpenAI-compatible example:

```json
{
  "id": "deepseek-main",
  "display_name": "DeepSeek",
  "method": "openai_compatible",
  "base_url": "fill the official OpenAI-compatible Base URL",
  "model": "fill the model name",
  "api_key_env": "DEEPSEEK_API_KEY",
  "capability_tags": ["general", "structure", "commercial_reverse"],
  "test_prompt": "ping"
}
```

CLI example:

```json
{
  "id": "claude-cli",
  "display_name": "Claude CLI",
  "method": "cli",
  "command": "fill your local non-interactive command",
  "capability_tags": ["long_context", "commercial_reverse", "general"],
  "test_prompt": "ping"
}
```

Health check:

```bash
python3 scripts/check_model_pool.py --config my-model-pool.json
```

Status meanings:

- `config_required`: no usable external model; output configuration guidance only.
- `low_confidence`: one external model is usable; low-confidence triage is allowed.
- `standard`: two to three external models are usable; analysis, opposition, and structure review can be assigned.
- `heavy_discussion`: four or more external models are usable; multi-perspective discussion can run.

Security rules:

- Keep only model names, call methods, and environment variable names in config files.
- Never commit real API keys, tokens, cookies, or account data.
- Codex is the host and should not be added to the external model pool.
- Missing settings or secrets are reported as `missing_config` / `missing_secret`; the Skill does not pretend they work.

## Community Evidence

The Skill does not lock users to a fixed list of platforms. It routes sources based on the idea, target user, industry, competitor, and scenario.

Typical source types include:

- product reviews;
- developer issues;
- Q&A communities;
- vertical forums;
- social comments;
- interview notes;
- local exported comment samples.

## Workflow

BLCaptain Opportunity PRD Skill follows an eight-step workflow:

1. Research: collect community comments, public URLs, local samples, competitor reviews, and reverse evidence.
2. Analyze: extract users, scenarios, behavior signals, commercial signals, and unknowns.
3. Plan: choose platform routes, methodology mix, validation actions, and P0 scope.
4. Develop: generate the engineering-ready PRD only after Go.
5. Verify: check evidence count, commercial signals, reverse evidence, and P0 evidence bindings.
6. Test: run scripts against structure, API, fields, exceptions, tests, and deployment sections.
7. Audit: check for local paths, real secrets, private data, and unsupported claims.
8. Summarize: output decision, stop conditions, next actions, and handoff files.

Research is the underlying action throughout the process. If evidence is insufficient, the workflow returns to research instead of inventing certainty.

## Install

Ask a Skill-capable agent:

```text
Install BLCaptain Opportunity PRD Skill from github.com/dososo/BLCaptain-Opportunity-PRD-Skill.
```

Or install manually:

```bash
npx skills add dososo/BLCaptain-Opportunity-PRD-Skill -g

git clone https://github.com/dososo/BLCaptain-Opportunity-PRD-Skill.git
cp -R BLCaptain-Opportunity-PRD-Skill ~/.codex/skills/BLCaptain-Opportunity-PRD-Skill
```

The repository name and Skill name are both aligned around **BLCaptain Opportunity PRD Skill**.

Requirements:

- Python 3.10+
- local command-line execution
- optional external model credentials stored in local environment variables, not in repository files

## Usage

After installation, start a new agent session and say:

```text
Use BLCaptain Opportunity PRD Skill to analyze:
I want to build an AI customer-service QA tool.

Check model configuration first, then provide platform routing, evidence wall,
reverse-evidence wall, and an opportunity assessment.
Generate a commercial and engineering PRD only if the Gates return Go.
```

Expected outputs:

1. model configuration status;
2. dynamic model role assignment;
3. intent card;
4. platform routing;
5. evidence wall;
6. reverse-evidence wall;
7. methodology conclusions;
8. Gate results;
9. opportunity assessment;
10. engineering-ready PRD only after Go.

## Local Commands

Basic validation:

```bash
python3 scripts/quick_validate.py
python3 scripts/simulate_user_flow.py
```

Model health check:

```bash
python3 scripts/check_model_pool.py \
  --config templates/model-pool.example.json
```

Scan community evidence:

```bash
python3 scripts/scan_community_evidence.py \
  --idea "AI customer-service QA tool" \
  --sources templates/community-sources.example.json
```

Scan reverse evidence:

```bash
python3 scripts/scan_reverse_evidence.py \
  --idea "AI customer-service QA tool" \
  --sources templates/community-sources.example.json
```

Run the full workflow:

```bash
python3 scripts/run_opportunity_workflow.py \
  --idea "AI customer-service QA tool" \
  --model-config templates/model-pool.example.json \
  --sources templates/community-sources.example.json \
  --output-dir tests/runs/opportunity-workflow
```

Validate an assessment or PRD:

```bash
python3 scripts/validate_opportunity_prd.py path/to/report-or-prd.md
```

## Data and Privacy

- Do not commit real credentials.
- Do not write real API keys into model config files.
- Do not bypass login walls or access private communities.
- Do not scrape production data by default.
- Public URLs can be snapshotted to local text for review.
- Generated run outputs go to `tests/runs/`, which is ignored by Git.
- `tests/fixtures/` contains synthetic samples for reproducible local validation.
- The Skill does not host any server; external model calls are handled by the user's own environment.

## Project Structure

```text
BLCaptain Opportunity PRD Skill/
├── SKILL.md
├── README.md
├── README.en.md
├── CHANGELOG.md
├── LICENSE
├── agents/
├── references/
├── templates/
├── scripts/
└── tests/fixtures/
```

## PRD Acceptance Standard

A Go PRD must include:

- traceable evidence IDs;
- reverse evidence and responses;
- P0 features bound to evidence;
- a 7-day validation plan;
- at least three acceptance scripts;
- engineering implementation sections;
- API contract, field dictionary, error codes, exception flows, test plan, deployment operations, and task DoD.

If these are missing, the PRD should not be handed to engineering.

## Author

Created and maintained by **BLCaptain**.

- GitHub: [@dososo](https://github.com/dososo)
- X / Twitter: [@thinkszyg](https://x.com/thinkszyg)
- Email: [blteam2026@outlook.com](mailto:blteam2026@outlook.com)
- Maintainer of the open-source Chinese Traditional Patterns Catalog: [wenyang.net](https://wenyang.net)

## License

MIT License. See [LICENSE](LICENSE).
