# FixLab product and scaling roadmap

This roadmap moves FixLab from a local/browser MVP toward a useful debugging product with a safe, reviewable GitHub workflow. Shipped capabilities and planned work are labeled separately; targets are proposals until measured. Track delivery in the [FixLab Product Roadmap project](https://github.com/users/uniyal802/projects/8).

## Current baseline

- **Local workbench:** Python HTTP server, synchronous Ollama analysis, SQLite session history, and Docker-based original-versus-proposed test runs.
- **Browser edition:** GitHub Pages static app, WebGPU inference, Pyodide test execution, and browser-local session history.
- **Engineering workflow:** GitHub Actions CI runs for pushes and pull requests.
- **Not implemented:** user accounts, hosted backend, repository import, issue tracking, coding-agent execution, GitHub Projects integration, or automatic pull request creation.

## Delivery principles

1. Keep all generated changes reviewable and require a human decision before applying them to a repository.
2. Treat repository content, model output, test code, and logs as untrusted input.
3. Keep secrets out of model prompts and test workers.
4. Establish product boundaries, privacy, and execution isolation before accepting public user code.
5. Measure latency, cost, reliability, and adoption before stating performance or business results.

## Milestones and scope

| Milestone | Scope | Status | Exit criteria |
| --- | --- | --- | --- |
| M0 · Working prototype | Local Ollama/Docker app and public browser edition | Complete | Both editions documented; CI and demo links available |
| M1 · Trustworthy public demo | Refined landing page, product workflow, labeled evaluation harness, honest limitations | In progress | Demo is easy to understand; dataset checks pass in CI; evaluation claims link to reproducible reports |
| M2 · Reliable local jobs | Durable job records, queue/worker interface, cancellation, retry, bounded logs | Planned | Restart-safe jobs with tested state transitions and hard deadlines |
| M3 · GitHub-connected investigations | Explicit repo authorization, branch/file selection, revision provenance | Planned | Revocable least-privilege access and owner-scoped source records |
| M4 · Reviewable coding-agent changes | Isolated agent task, constrained branch, CI results, user-approved pull request | Planned | Agent output is auditable; no automatic merge; user approves PR creation |
| M5 · Hosted service | Identity, quotas, durable storage, hardened execution workers, monitoring, rollback | Planned | Tenant isolation and operational readiness demonstrated before public code execution |

## Step-by-step plan

### Step 1 — Make the repository and demo portfolio-ready

**Status: in progress.**

- Explain the current product workflow, architecture, setup, verification, evaluation method, and known limitations.
- Make the public browser edition communicate the workflow and its real trust boundaries clearly.
- Keep resume wording grounded in features that exist and can be demonstrated.
- Add contribution guidance, coding-agent instructions, and pull request/issue templates.
- Add prominent links to the source, CI, live browser edition, and roadmap.

**Acceptance:** a new developer can run the project, understand the two editions, reproduce the demo, and distinguish shipped features from roadmap items. The benchmark validates every reference fix and fails the build if any case is inconsistent.

### Step 2 — Use GitHub for visible project planning

- Create a GitHub Project board for roadmap work, with fields such as status, priority, milestone, and area.
- Track repository integration, durable jobs, tenant safety, and execution isolation as separate epics/issues.
- Add labels and issue templates so bugs and feature requests arrive with useful context.
- Link the project board from the repository README once its real URL exists.

**Acceptance:** each planned capability has an issue with scope and acceptance criteria; the board shows current status and the next milestone.

### Step 3 — Add repository-aware investigations

- Let a user authorize a GitHub repository with minimum required permissions.
- Select a branch and file or provide a failing test/issue as investigation context.
- Read only the selected content, record source revision identifiers, and preserve repository provenance in each investigation.
- Never execute repository code in the API process.

**Acceptance:** repository access can be revoked; a saved investigation identifies its source revision; tests cover unauthorized repositories and cross-account access.

### Step 4 — Add a controlled coding-agent workflow

- Define an agent task contract: repository, base revision, allowed files, requested change, test command, and resource limits.
- Run the agent in an isolated, disposable worker with no production credentials and bounded network access.
- Persist task status, logs, outputs, and cancellation; make each result reproducible from its base revision.
- Require human review before any code is applied or pushed.

**Acceptance:** tasks can be queued, cancelled, retried safely, and audited; one task cannot read another task's checkout or secrets.

### Step 5 — Open reviewable pull requests

- Create a branch from the authorized base revision and apply the reviewed patch.
- Run configured checks before offering a PR.
- Show the full diff, test results, source revision, and agent/model disclosure before creation.
- Request only the repository permissions required to create a branch and pull request; do not merge automatically.

**Acceptance:** the user explicitly approves PR creation; branch and PR links are saved to the investigation; rejected or failed checks prevent the PR flow from claiming success.

### Step 6 — Build the hosted service foundation

- Move long-running analysis and execution to a durable job queue and worker process.
- Add accounts, authorization, owner-scoped records, quotas, retention controls, and bounded logs/storage.
- Move from single-process SQLite to a managed production database when multiple API instances are needed.
- Select and review an execution isolation service appropriate for hostile code before accepting public jobs.
- Add metrics for queue delay, job duration, completion/failure rates, worker saturation, and cost.

**Acceptance:** workers recover jobs after restart, users can access only their own data, resource limits are enforced, and operators can observe service health and per-job cost.

### Step 7 — Deploy and publish an evidence-based demo

- Keep the GitHub Pages browser edition as the low-cost public demo.
- Deploy the hosted API only after authentication, tenant boundaries, quotas, and worker isolation are in place.
- Add a health endpoint, backups, database migrations, logs/alerts, and a rollback procedure.
- Publish a deploy link and record the commit/release associated with each demo.

**Acceptance:** deployment is reproducible, the public URL is health-checked, and the demo's data handling and limitations are documented.

## First implementation slice

After the public demo/evaluation milestone, the next code milestone should be **durable jobs**, because both model inference and test execution are slow synchronous requests today. Implement job records and state transitions, then submit/status/result/cancel endpoints and a separate worker entry point. Preserve the local workflow while moving execution behind the worker interface. This creates the foundation for bounded concurrency before adding accounts, repository access, agents, or pull requests.

Suggested initial service objectives to validate with real measurements:

- Job submission responds within 500 ms at the 95th percentile.
- Queue wait stays under 30 seconds at the initial worker capacity.
- Every job has a hard deadline and bounded output.
- Jobs cannot read each other's source, results, or logs.

These are proposed starting targets, not current measurements or guarantees.

## Release sequence

1. Merge portfolio and contribution documentation.
2. Set up the GitHub Project board and prioritize scoped issues.
3. Implement and validate the durable job layer locally.
4. Add identity, tenant-safe storage, and quotas.
5. Review and build isolated workers.
6. Add repository authorization, agent tasks, and user-approved PR creation.
7. Deploy the hosted service and publish measured results.
