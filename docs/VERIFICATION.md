# Verification

Run `python3 -m unittest discover -s tests -v` from the project directory.

Tests cover invalid AI output, missing module imports, persistence, revision invalidation, API review/edit/delete behavior, cross-origin write rejection, fail-closed Docker execution, trusted runner fixtures, coverage reporting, empty suites and all-skipped suites.

Docker integration tests cover original fail/fixed pass, empty suites, and network isolation. They require the `fixlab-runner:local` image and Docker daemon. CI builds the image before running tests.

During project preparation, a real local Ollama `qwen2.5-coder:7b` request returned analysis, corrected code and tests for the empty-list average example. Missing imports from the generated tests exposed an integration issue that is now automatically repaired and unit-tested. The live dashboard showed AI Ready.

Docker was not installed on the preparation machine. Container integration tests are provided but not claimed as locally verified. User requested completion of project files without installing Docker.

Browser edition: the live runtime check was executed in Chrome. Original average([]) failed; repaired average([]) and normal-input tests passed (2 tests; 100% statement-line coverage). WebGPU initialized on the Apple GPU. AI output verification is recorded after actual inference.
