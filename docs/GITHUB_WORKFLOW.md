# GitHub workflow for FixLab

## Available today

- GitHub Actions validates pushes and pull requests with Python, Docker integration coverage, and JavaScript syntax checks.
- Issue forms capture reproducible bug reports and scoped feature requests.
- The pull request template prompts for verification evidence and safety review.
- `AGENTS.md` and `.github/copilot-instructions.md` give coding agents repository-specific context and constraints.
- The browser edition is published through GitHub Pages.
- The [FixLab Product Roadmap board](https://github.com/users/uniyal802/projects/8) tracks the next milestones.

## Set up the project board

The FixLab Product Roadmap board is available at [github.com/users/uniyal802/projects/8](https://github.com/users/uniyal802/projects/8). It was created as a board and is configured to import issues from `fixlab`. Its initial status columns are **Todo**, **In Progress**, and **Done**. Add a **Ready** or **In Review** status if the workflow needs more detail.

Add `Priority` (P0–P3), `Area` (Product, GitHub integration, Agents, Scaling, Security, Documentation), and `Milestone` fields. Use roadmap steps as epics and link each implementation issue to its acceptance criteria in [`SCALE_ROADMAP.md`](../SCALE_ROADMAP.md). Keep the first milestone small: contribution docs and project setup, followed by a durable local job queue.

## Pull request flow

1. Create a branch for one issue or milestone slice.
2. Link the pull request to the issue using `Closes #<number>` when appropriate.
3. Describe behavior changes and list the exact checks run; disclose checks that could not run.
4. Include screenshots for UI changes and update docs for API, setup, or security changes.
5. Let GitHub Actions finish and review the complete diff before merging.

The template is at [`.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md). GitHub Actions CI is configured in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

## Coding-agent workflow

Use repository agents to draft scoped changes and run verification, not to merge or deploy automatically. Provide an issue, acceptance criteria, and the relevant roadmap step. Review any generated diff and test output. Do not provide production credentials to an agent or allow it to run submitted project code outside the documented runner boundary.

Repository instructions live in [`AGENTS.md`](../AGENTS.md) and [`.github/copilot-instructions.md`](../.github/copilot-instructions.md). The GitHub Agents tab may expose platform-specific coding agents depending on account and repository settings; the existence of that tab does not mean FixLab itself has an agent integration.

## Deployment links

- **Browser demo:** [https://uniyal802.github.io/fixlab/](https://uniyal802.github.io/fixlab/)
- **GitHub Actions:** [workflow runs](https://github.com/uniyal802/fixlab/actions/workflows/ci.yml)
- **Repository deployments:** [GitHub deployments](https://github.com/uniyal802/fixlab/deployments)

The Pages deployment is the browser edition only. It does not host the Ollama/SQLite/Docker backend. A hosted backend requires the safety, identity, job, and operations work in the roadmap.
