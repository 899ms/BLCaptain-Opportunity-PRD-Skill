# Changelog

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
