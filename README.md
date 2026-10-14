# FixLab — AI Debugging & Testing Assistant

A runnable local MVP combining bug analysis, reviewable patches, generated regression tests, session history, and original-versus-fixed execution.

## Features

- Real local AI analysis with Ollama and syntax-validated patches.
- Missing solution imports in generated tests repaired automatically.
- Python file import, diff/code/test tabs and editable revisions.
- Isolated original-versus-fixed runs and numeric coverage reports.
- Review decisions, saved history, session deletion, JSON and Python exports.
- Live AI/Docker readiness indicators.
- Unit/API tests, Docker integration tests and GitHub Actions CI.

## Start the dashboard

Requires Python 3.9+. No Python packages are required.

```sh
cd /path/to/fixlab
./start.sh
```

Open http://127.0.0.1:8000. Click **Load example**, then **Analyze & generate tests**.

## Connect real AI

Install Ollama from https://ollama.com, start it, and pull the model:

```sh
ollama pull qwen2.5-coder:7b
```

Ollama normally listens at http://127.0.0.1:11434. Set `OLLAMA_URL` and `OLLAMA_MODEL` in the server environment to change these. Hardware requirements and latency depend on the model. No simulated AI results are returned when the provider is unavailable.

## Enable test execution

Install and start Docker, then build the local runner image:

```sh
docker build -f Dockerfile.runner -t fixlab-runner:local .
```

Review generated code and tests, then click **Run isolated tests**. Each version runs with no network, a read-only root and submission mount, an unprivileged user, dropped capabilities, process/CPU/memory limits, and a 20-second timeout. There is no host-code execution fallback. The dashboard reports test counts, failures, errors, skips, execution time, and AST statement-line coverage of solution.py; this is not branch coverage. Zero-test and all-skipped suites fail. Output displayed per run is capped at 32 KB.

Docker is a development isolation boundary, not a hardened public multi-tenant execution service. Do not expose this MVP publicly. Before production, add authentication, authorization, stronger execution isolation, job quotas, bounded disk/log storage, and deployment-specific security review. AI-generated tests can be wrong and passing tests do not prove correctness.

## Architecture

- `frontend/`: responsive dashboard, patch/test tabs, review, exports, history.
- `backend/server.py`: same-origin HTTP API, bound to loopback.
- `backend/core.py`: Ollama integration, response validation, unified diffs, SQLite persistence, container orchestration.
- `backend/runner.py`: unittest discovery and failure propagation.
- `data/sessions.db`: generated locally; excluded from source control.

This first version uses vanilla JavaScript, standard-library Python and SQLite so it runs without package installation. React, FastAPI and PostgreSQL migration, GitHub integration, background jobs, remain future work. Numeric statement-line coverage is included.

## Project documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Demo and resume notes](docs/DEMO.md)
- [Verification](docs/VERIFICATION.md)

## API

- `GET /api/health`: local model and Docker/image readiness.
- `POST /api/edit`: `{ "id": "...", "fixed_code": "...", "tests": "..." }`; resets evidence and review.
- `POST /api/delete`: `{ "id": "..." }`; permanently deletes the local session.
- `POST /api/analyze`: `{ "code": "...", "error": "..." }`
- `GET /api/sessions` and `GET /api/sessions/<id>`
- `POST /api/run`: `{ "id": "..." }`
- `POST /api/review`: `{ "id": "...", "review": "accepted" }` (or `rejected`)

Accepting a patch records a review decision; it does not alter a repository. Saved results and source can be exported as JSON. Sessions are stored locally in plaintext.

## Verification

```sh
python3 -m unittest discover -s tests -v
```

Unit/API tests cover validation, imports, persistence, revisions, routes, trusted runner reports and refusing execution without Docker. Docker integration tests run when the local image and daemon are available. To verify the complete flow, run the example with Ollama and Docker configured and confirm the original fails while the fixed module passes.

## Portfolio demo

Show the empty-list average bug, AI explanation, patch diff, regression tests, original failure, fixed pass, coverage output, and saved review. Record measured results before making performance or reliability claims in your resume.

References: [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md), [Docker run](https://docs.docker.com/reference/cli/docker/container/run/).
