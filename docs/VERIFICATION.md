# Verification record

This document describes the checks in the repository and records previously documented verification. Re-run the commands against the current revision before making a new release or publishing a fresh verification claim.

## Run the automated suite

From the repository root:

```bash
python3 -m unittest discover -s tests -v
```

The suite covers input and AI-response validation, import normalization, SQLite persistence, revision invalidation, API review/edit/delete behavior, cross-origin write rejection, fail-closed Docker execution, runner reports, coverage output, and empty or all-skipped test suites.

Docker integration coverage includes original-failure/proposed-pass behavior, empty suites, and network isolation. It requires a running Docker daemon and the `fixlab-runner:local` image. GitHub Actions builds that image before running the suite.

The CI workflow also checks syntax for `frontend/app.js`, `docs/app.js`, and `docs/browser.js`.

## Previously recorded checks

The repository's prior verification notes recorded:

- A local Ollama `qwen2.5-coder:7b` analysis of the empty-list average example, including corrected code and tests.
- A browser run in Chrome using WebGPU and Pyodide: the original `average([])` failed, while the proposed implementation passed two tests with 100% statement-line coverage for that example.
- GitHub Actions run `38566737696` completed successfully, including Docker integration tests.
- Docker integration tests were not run on the original preparation machine because Docker was unavailable there.

These are historical records from earlier project preparation, not a fresh run against every later change. Re-run CI and the demo before reusing them in a resume, release, or project presentation.

## What these checks do not establish

- A passing test suite does not prove code correctness or security.
- Statement-line coverage is not branch coverage.
- Local Docker settings do not establish a safe public multi-tenant execution service.
- CI passing does not mean the application has authentication, user accounts, hosted AI, repository integration, or production deployment of its backend.
