# Changelog

## v1.2.9

### Added

- Added shared OpenAI-compatible payload construction and assistant response parsing.
- Added strict health-check coverage for HTTP 200 responses with empty `message.content`.
- Added simulation coverage for reasoning-only responses, empty responses, and `extra_body.thinking.disabled` payloads.

### Changed

- Health checks now require final `choices[0].message.content`; `reasoning_content` alone is not treated as a usable model output.
- Updated workflow model invocation to fail clearly when a model returns no final content.
- Updated DeepSeek and GLM connection presets with current project defaults, `max_tokens`, and disabled thinking for short review tasks.
- Clarified README and reference docs so model setup stays inside this Skill's own model pool and avoids unrelated setup paths.

### Verified

- `python3 -m py_compile scripts/*.py`
- `python3 scripts/quick_validate.py`
- `python3 scripts/simulate_user_flow.py`
- `python3 scripts/setup_model_pool.py connect deepseek --store auto --dry-run`
- `python3 scripts/check_model_pool.py --config templates/model-pool.providers.example.json`
- `python3 scripts/run_opportunity_workflow.py --idea "Codex 国内用户痛点解决方案" --model-config tests/fixtures/model-pool-cli.json --sources tests/fixtures/community-codex-broad-sources-local.json --reverse-sources tests/fixtures/community-codex-reverse-sources-local.json --output-dir tests/runs/opportunity-workflow-codex-cut --run-discussion`
- `python3 scripts/validate_opportunity_prd.py tests/runs/opportunity-workflow-codex-cut/commercial-opportunity-prd.md`
- Sensitive information and unrelated reference-trace audit

## v1.2.8

### Added

- Added `setup_model_pool.py connect <model>` for one-step model connection.
- Added `--store auto` secret storage selection:
  - macOS Keychain
  - Windows DPAPI user-level encryption
  - Linux Secret Service
  - environment-variable fallback guidance when secure storage is unavailable
- Added `secret_ref` support in model health checks and workflow model invocation.
- Added simulation coverage for safe API-key setup without writing real keys to model-pool JSON.

### Changed

- Made “connect the model, then safely save the key” the default onboarding path.
- Reframed environment variables as an advanced or fallback option instead of the primary new-user path.
- Updated README, Skill instructions, templates, and model configuration references to explain cross-platform secure storage.

### Verified

- `python3 -m py_compile scripts/*.py`
- `python3 scripts/setup_model_pool.py connect deepseek --store auto --dry-run`
- `python3 scripts/setup_model_pool.py connect deepseek --store env --api-key-env BLCAPTAIN_TEST_DEEPSEEK_KEY --config tests/runs/secure-connect-model-pool.json`
- `python3 scripts/check_model_pool.py --config tests/runs/secure-connect-model-pool.json`
- `python3 scripts/quick_validate.py`
- `python3 scripts/simulate_user_flow.py`
- Sensitive information and unrelated reference-trace audit

## v1.2.7

### Added

- Added first-run model Agent onboarding with supported Agent types, safe local config path, and health-check guidance.
- Added `scripts/setup_model_pool.py` for `--doctor` and `--init` model-pool bootstrap flows.
- Added model Agent catalog and first-run onboarding references.
- Added pain-cluster analysis and Cut-to-Go reassessment for broad Watch/Pivot opportunities.
- Added Codex broad-pain fixtures to verify that a broad community signal can be narrowed into a model-setup opportunity PRD.

### Changed

- Updated the Skill entry flow so model-pool Bootstrap is visible before community evidence analysis.
- Updated Watch/Pivot handling to explain why no PRD is generated, then attempt a narrower Cut-to-Go when evidence supports it.
- Updated Chinese and English READMEs to surface first-run model Agent setup at the top.
- Updated validation and simulation scripts to fail if first-run onboarding or Cut-to-Go coverage disappears.

### Verified

- `python3 -m py_compile scripts/*.py`
- `python3 scripts/quick_validate.py`
- `python3 scripts/simulate_user_flow.py`
- `python3 scripts/setup_model_pool.py --doctor --config tests/runs/new-user-model-pool.json`
- Codex broad-pain Cut-to-Go workflow generates and validates a commercial + engineering PRD
- Sensitive information and unrelated reference-trace audit

## v1.2.6

### Added

- Added model-pool Bootstrap as the hard first stage for the end-to-end workflow.
- Added CLI and OpenAI-compatible connection candidate discovery in model health checks.
- Added structured `--json-output` support for model health checks.
- Added Pivot-to-Go loop for opportunities that need a narrower cut before PRD generation.

### Changed

- Stopped `run_opportunity_workflow.py` at `ConfigRequired` when no external model passes the skill-owned model pool health check.
- Restricted discussion execution to models registered in the model pool and passing health checks.
- Updated Chinese and English docs to clarify that discovered candidates do not count as usable models until configured and checked.
- Replaced plaintext-looking API key export examples with safer environment-variable guidance.

### Verified

- `python3 -m py_compile scripts/*.py`
- `python3 scripts/quick_validate.py`
- `python3 scripts/simulate_user_flow.py`
- ConfigRequired workflow stops before evidence scan, discussion, Gate, or PRD generation
- Go workflow generates and validates commercial + engineering PRD
- Pivot-to-Go workflow preserves reverse evidence, reruns Gate, and validates generated PRD
- Sensitive information and reference-trace audit

## v1.2.5

### Added

- Added a simpler Codex-assisted model setup path for new users.
- Documented user-friendly prompts for connecting DeepSeek, GLM, Claude CLI, Gemini, Grok, and local CLI models.

### Changed

- Made Codex-assisted setup the recommended path in Chinese and English README files.
- Updated model configuration guidance, health-check output, and simulation fixtures so users do not need to start by editing JSON manually.
- Kept manual JSON configuration as the advanced fallback for users who want full control.

### Verified

- `python3 scripts/quick_validate.py`
- `python3 scripts/simulate_user_flow.py`
- `python3 -m py_compile scripts/check_model_pool.py scripts/run_opportunity_workflow.py scripts/prepare_real_run.py scripts/simulate_user_flow.py scripts/quick_validate.py`
- New-user install simulation from a fresh GitHub clone
- Sensitive information and reference-trace audit

## v1.2.4

### Changed

- Unified the public GitHub repository name, install commands, README links, and Skill frontmatter name around `BLCaptain Opportunity PRD Skill`.
- Removed the old repository slug from public documentation.

## v1.2.3

### Added

- Added `README.en.md` for English-speaking users.

### Changed

- Unified user-facing Skill naming as `BLCaptain Opportunity PRD Skill`.
- Kept the machine-readable Skill identifier and repository slug only where they are required for loading or installation.
- Updated generated report titles, interface metadata, and HTTP User-Agent tokens to use the public Skill name.

## v1.2.2

### Changed

- Clarified the public release boundary for generated run outputs and synthetic test fixtures.
- Changed generated workflow and model-health reports to display repository-relative paths when outputs stay inside the project.
- Removed local ignored run-output directories from the release workspace.

### Verified

- Confirmed there are no empty local release directories.
- Confirmed `tests/runs/` is not tracked by Git.
- Confirmed tracked files do not contain local path or private source traces.

## v1.2.1

### Changed

- Rewrote reachable Git history for the public release so historical local path traces are no longer present.
- Preserved public author metadata as release attribution.
- Kept package behavior unchanged except release metadata.

### Verified

- `python3 -m py_compile scripts/*.py`
- `python3 scripts/quick_validate.py`
- `python3 scripts/simulate_user_flow.py`
- `python3 scripts/validate_opportunity_prd.py tests/fixtures/go-customer-service.md`
- `python3 scripts/validate_opportunity_prd.py tests/fixtures/nogo-trend-only.md`

## v1.2.0

### Added

- Added MIT `LICENSE`.
- Added public-facing README sections for License and Author.

### Changed

- Rewrote README for public GitHub release.
- Removed internal process documents from the public package scope.
- Replaced provider-specific model examples with neutral model placeholders.
- Removed local absolute path handling from generated PRD source validation.
- Updated real-run snapshots to use repository-relative paths when possible.

### Verified

- `python3 -m py_compile scripts/*.py`
- `python3 scripts/quick_validate.py`
- `python3 scripts/simulate_user_flow.py`
- `python3 scripts/validate_opportunity_prd.py tests/fixtures/go-customer-service.md`
- `python3 scripts/validate_opportunity_prd.py tests/fixtures/nogo-trend-only.md`
