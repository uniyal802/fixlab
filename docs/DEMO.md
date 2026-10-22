# Portfolio demo and resume notes

## Five-minute product walkthrough

1. Open the [browser edition](https://uniyal802.github.io/fixlab/) or run the local edition using the [setup guide](../README.md#run-locally).
2. Show the sample `average([])` failure and explain the expected behavior.
3. Run analysis and inspect the explanation, proposed patch, and generated regression tests.
4. Run the same tests against original and proposed code. Show the result comparison and statement-line coverage.
5. Edit a test, save the revision, and show that previous execution results and the review decision are cleared.
6. Accept or reject the patch, then export the session.
7. Close with the design boundaries: local inference or on-device inference, no automatic repository modification, and the difference between statement-line and branch coverage.

## Resume bullet

Use only after reproducing the end-to-end flow yourself:

> Built FixLab, an AI-assisted Python debugging workbench that generates reviewable patches and regression tests, compares original and proposed code in isolated runners, and reports test and statement-line coverage using Ollama, SQLite, and Docker.

For the browser edition, you can mention WebGPU and Pyodide if you can explain their roles and limitations.

## Keep claims evidence-based

Do not claim user counts, accuracy, speedups, percentage improvements, production readiness, or GitHub automation without measured evidence and a working implementation. The FixLab application does not currently integrate with GitHub repositories, pull requests, Projects, or coding agents.

## Evidence to capture

- A short screen recording of the full debugging workflow.
- A link to the repository and its passing CI history.
- The exact model, browser, and hardware used for a live demo.
- Test counts and coverage from a reproducible run, described as statement-line coverage.
- Any performance measurements with the workload, hardware, and measurement method.
