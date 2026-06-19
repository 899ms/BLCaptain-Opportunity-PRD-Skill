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

- No usable model: output only a short configuration guide.
- One usable model: run in low-confidence single-model mode.
- Multiple usable models: assign analysis, reverse review, structure, external view, or implementation roles based on actual capability tags.

The workflow is always hosted by Codex or the current coding agent. The Skill does not hard-code fixed duties for any specific model brand.

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

## License

MIT License. See [LICENSE](LICENSE).

## Author

Created and maintained by **BLCaptain**.

- GitHub: [@dososo](https://github.com/dososo)
- X / Twitter: [@thinkszyg](https://x.com/thinkszyg)
- Email: [blteam2026@outlook.com](mailto:blteam2026@outlook.com)
