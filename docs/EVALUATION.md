# Evaluation harness

The harness measures how well FixLab's AI analysis repairs bugs, using ground truth the model never sees. It is the source of any accuracy figure you put on a resume: report what a run produced, with the model name, case count and date.

## Dataset

`evaluation/cases.py` holds 21 original, hand-written Python bug cases across eight bug classes (off-by-one, empty input, wrong operator, shared mutable state, string handling, boundary conditions, wrong algorithm, recursion). Each case has:

- `code`: the buggy module and `error`: the bug report given to the model (symptom plus expected behavior)
- `fixed`: an independent reference solution and `tests`: independent reference tests (never shown to the model)

`tests/test_evaluation.py` enforces that every case's reference tests fail on `code` and pass on `fixed`. `python3 -m evaluation.run_eval --check-dataset` repeats that check inside the Docker runner (CI does this).

## Metrics

| Metric | Definition |
| --- | --- |
| Valid analysis | The model returned usable, syntax-valid fields |
| Discriminating tests | Generated tests fail on the buggy code and pass on the model's fix |
| Fix correct | The model's fix passes the independent reference tests |
| Verified fix | Fix correct and discriminating tests: a repair FixLab can also demonstrate |
| Mutation detection | Of the AST mutants of the model's fix that the reference tests catch, the share the generated tests also catch |

Every rate is reported with a 95% Wilson interval. Docker or runner failures are recorded as infrastructure errors and excluded from denominators, so they never count against the model. Mutation analysis runs only when a fix passes both reference tests and the generated tests. Mutants the reference tests cannot distinguish are treated as equivalent and ignored.

## Running it

Prerequisites: Ollama running with the model pulled, Docker running, and the runner image built (`docker build -f Dockerfile.runner -t fixlab-runner:local .`).

```sh
python3 -m evaluation.run_eval --check-dataset
python3 -m evaluation.run_eval --model qwen2.5-coder:7b
python3 -m evaluation.run_eval --model qwen2.5-coder:1.5b
```

Useful flags: `--ids a,b`, `--limit N`, `--mutants N` (0 disables mutation analysis), `--seed`, `--out DIR`. Each run writes `results.json` (per-case results, including the model's code and tests) and `report.md` under `evaluation/results/<model>-<timestamp>/`. A full run executes several containers per case; expect minutes to tens of minutes depending on the model and hardware.

## Limits to state honestly

- 21 small functions measure relative differences between models and prompts, not general debugging ability. Confidence intervals are wide at this size; grow the dataset before drawing fine conclusions.
- Each run is a single sample per case. Model output varies between runs; repeat runs and report the spread if you compare models closely.
- Passing reference tests is strong evidence for these small functions, not a proof of correctness.
- The dataset is public in this repository, so it could be included in a model's training data.
- `evaluation/local_exec.py` runs code on the host without isolation and is used only for the repository's own trusted dataset and harness unit tests, never for AI-generated code.

## Resume wording

Add figures only after a real run, and quote the dataset size and model: for example, "Evaluated an AI debugging pipeline on a 21-case labeled benchmark with independent reference tests and mutation analysis; [model] reached [X]% verified-fix rate (95% CI [a]–[b]%)."
