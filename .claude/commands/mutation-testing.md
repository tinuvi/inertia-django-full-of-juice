---
description: Run mutation testing on a target file with mutmut and iteratively close test gaps
---

# Mutation Testing Workflow

Drive a mutation-testing pass on a single target file in `inertia/` using `mutmut`. Improve the test suite by writing new assertions that kill surviving mutants, **without modifying the library source**.

The repo's library code lives in `inertia/`; tests live alongside it under `inertia/tests/test_*.py` (flat layout — no nested `tests/inertia/...` mirror). The Django settings module is `inertia.tests.settings`. Everything runs inside the `integration-tests` service from `docker-compose.yml`.

Django bootstrap is **not** baked into the repo. mutmut drives tests through repeated `pytest.main()` calls, so the first-time setup adds a root `conftest.py` (see Phase 0) and `also_copy`s it into `mutants/`. The bootstrap is guarded on `django.test.utils._TestState` so the repeated invocations stay idempotent — see https://github.com/boxed/mutmut/issues/504.

## Prerequisites

Before running any mutmut command, confirm these two inputs. If the user did not provide them in the invoking prompt, **ask and wait** for an answer — do not guess.

1. **Target module.** The exact path of the library source file to mutate (e.g., `inertia/http.py`, `inertia/middleware.py`, `inertia/utils.py`). Must have a colocated test file under `inertia/tests/test_*.py` (e.g., `inertia/tests/test_middleware.py`). Files under `inertia/tests/` themselves are out of scope.
2. **Git worktree mode.** Whether to run inside a dedicated git worktree or in the current checkout:
   - **Worktree**: isolates `mutants/`, `mutants.sqlite`, the new `[tool.mutmut]` block in `pyproject.toml`, and the root `conftest.py` from the main checkout. Required if running mutation testing on several files in parallel or to keep the main checkout clean.
   - **In-place**: runs in the current directory. Fine for a one-off, sequential session. Leaves `[tool.mutmut]` in `pyproject.toml`, `conftest.py` at the repo root, and a `mutants/` dir behind until cleaned up.

   If unspecified, ask: "Run this session in a new git worktree (parallel-safe, isolated) or in the current checkout (simpler, sequential-only)?" Wait for the answer.

   **Docker Compose isolation when using a worktree.** Pass `-p <slug>` to every `docker compose` command (e.g. `-p inertia-mut-middleware`). Use the same slug for every command in the session.

## Golden Rules

1. **Never modify library source** (`inertia/*.py` outside `inertia/tests/`) during a mutation pass without explicit user permission. Tests are in scope; source is read-only. If a surviving mutant points to a real bug or dead code, **stop and report it** — do not silently fix.
2. **100% score is unlikely to happen.** Logging-argument mutants and no-ops are expected survivors — the project mandates parameterized logging (`logger.info("msg %s", x)`), and asserting on log argument shape is brittle.
3. **One target file at a time.** Don't mutate the whole `inertia/` package in a single run.
4. **Tests must pass under the project's canonical runner** (`python manage.py test`) before and after changes, not just under pytest. Mutmut uses pytest to drive tests; the project uses Django's unittest runner — both must agree. The repo entrypoint is `docker compose run --remove-orphans --rm integration-tests`, which runs `coverage run --source='.' manage.py test --durations 10 --timing --parallel`.
5. **v3 protocol changes.** If a surviving mutant exposes a behavior in `inertia/http.py` or `inertia/middleware.py` that touches the v3 protocol surface (headers, page-object fields, prop kinds), the new test must reflect what the spec or Laravel's `inertiajs/inertia-laravel@3.x` reference actually does. Brief the `protocol-researcher` or `laravel-comparator` subagents rather than guessing.

## Phase 0 — One-time bootstrap (skip if already done)

mutmut needs a root `conftest.py` so Django is configured at pytest collection time. Create it once per checkout (or per worktree). Both files below are gitignored / transient in the worktree case.

**Create `conftest.py` at the repo root:**

```python
from __future__ import annotations

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inertia.tests.settings")

import django  # noqa: E402

django.setup()

from django.test.runner import DiscoverRunner  # noqa: E402
from django.test.utils import _TestState, setup_test_environment  # noqa: E402

if not hasattr(_TestState, "saved_data"):
    setup_test_environment()
    _runner = DiscoverRunner(verbosity=0, keepdb=True)
    _runner.setup_databases()
```

Why `_TestState.saved_data` and not a module-level flag: pytest re-imports `conftest.py` between `pytest.main()` calls and wipes module globals, but Django's `_TestState` class attribute persists across reimports. See mutmut issue #504.

`mutants/` and `mutants.sqlite` are already covered by the repo's `.gitignore` (line 147: `mutants`). Don't track them.

## Phase 1 — Configure the target

Add a `[tool.mutmut]` section to `pyproject.toml`:

```toml
[tool.mutmut]
paths_to_mutate = ["inertia"]
# Update per target:
pytest_add_cli_args_test_selection = [
    "inertia/tests/test_<target>.py",
]
also_copy = ["conftest.py"]
debug = false
```

**Why each key:**
- `paths_to_mutate = ["inertia"]` — the whole package must be copied to `mutants/` so intra-project imports (e.g. `http.py` importing `prop_classes.py`) still resolve under the mutated tree. Restrict mutation via the CLI argument in Phase 2, not by narrowing this.
- `pytest_add_cli_args_test_selection` — narrows pytest collection to the one test file, avoiding unrelated sibling tests and the slower full-suite import.
- `also_copy = ["conftest.py"]` — ships the root bootstrap into `mutants/` so Django is configured against the mutated tree. Required for any target whose tests hit Django machinery (middleware, ORM, signals, template rendering); harmless otherwise.
- `debug` — prints the pytest invocation on each run. Useful when diagnosing bootstrap failures.

**Why `type_check_command` is intentionally absent.** mutmut transpiles every source file to wrap each function in a `_mutmut_trampoline` dispatcher. The repo's `[tool.mypy]` is `strict = true`, which rejects the trampoline (untyped calls, unused `# type: ignore`, `Any` returns) — verified empirically: a vanilla `mypy inertia` against the `mutants/` tree reports 747 errors. With `type_check_command = ["mypy", "inertia"]`, every mutant would be falsely marked 🧙 (caught by type check) and pytest would never actually run. If you want a pre-filter, configure a relaxed mypy invocation (e.g. `mypy --no-strict-optional --disable-error-code=no-untyped-call --disable-error-code=unused-ignore --disable-error-code=no-any-return inertia`) and verify it doesn't blanket-reject before relying on the count.

Only `pytest_add_cli_args_test_selection` changes between targets. The other keys stay.

**Wipe prior state when switching targets:**

```bash
docker compose run --remove-orphans --rm integration-tests bash -c 'rm -rf mutants mutants.sqlite'
```

`mutants.sqlite` caches mutant IDs, exit codes, and the test-selection map from the previous run. If you don't wipe it when switching targets, mutmut will reuse stale entries and produce misleading results. Do **not** wipe between iterative re-runs on the same target (Phase 7) — that cache is what makes already-killed mutants skip instantly.

## Phase 2 — Run mutmut

Pass the target module as a dotted-path glob so mutmut only exercises mutants in that file:

```bash
docker compose run --remove-orphans --rm integration-tests \
  mutmut run "inertia.<target>*"
```

For example, mutating `inertia/middleware.py` is `mutmut run "inertia.middleware*"`. Mutants for other files are still generated (they must be, for import resolution), but they are skipped at the testing phase.

Output legend (mutmut prints these emojis — they are tool output, not decoration):

| Symbol | Status | Meaning |
|---|---|---|
| 🎉 | killed | A test caught the mutation — good |
| 🧙 | caught by type check | A `type_check_command` rejected the mutant before pytest ran (zero by default — see Phase 1) |
| 🙁 | survived | No test caught it — **this is where we work** |
| 🫥 | no tests | No test covers the mutated code — hole in selection |
| ⏰ | timeout | Mutant caused an infinite loop — usually a killed mutant |
| 🤔 | suspicious | Test passed but unreliably — investigate |
| 🔇 | skipped | Explicitly ignored |

## Phase 3 — Read the report

List surviving mutant IDs:

```bash
docker compose run --remove-orphans --rm integration-tests bash -c 'mutmut results 2>&1 | grep "survived"'
```

Diff for one mutant:

```bash
docker compose run --remove-orphans --rm integration-tests \
  mutmut show '<mutant.id.from.results>'
```

**Bulk triage via `scripts/triage_mutmut_survivors.py`.** Recommended when the survivor count is >30. The script calls mutmut's Python API in-process (fast: ~seconds for hundreds of survivors), buckets each survivor purely by mutation shape (`short_circuit_flip`, `comparison_flip`, `boolean_flip`, `arg_to_none`, `kwarg_removed`, `default_value_change`, `number_change`, `string_change`, `operator_change`, `identifier_swap`, plus `logger_noise` / `noop` low-value), and reports HIGH / LOW / UNKNOWN tiers plus a per-function summary. No project-specific constants — works for any target.

```bash
# Fetch + classify in one command. <target> is the file stem (e.g. "http", "middleware").
docker compose run --remove-orphans --rm integration-tests \
  python scripts/triage_mutmut_survivors.py --target <target>

# Narrow to one function / bucket:
docker compose run --remove-orphans --rm integration-tests \
  python scripts/triage_mutmut_survivors.py \
    --target <target> \
    --function render --bucket comparison_flip

# Hide diffs for a one-page overview:
docker compose run --remove-orphans --rm integration-tests \
  python scripts/triage_mutmut_survivors.py --target <target> --no-diffs
```

Triage rules:
- UNKNOWN > 0: inspect manually before writing any test — the classifier was not confident.
- LOW tier (`logger_noise`, `noop`): accept as survivors, do not chase.
- HIGH tier: Phase 5 bug-check each, then Phase 6.
- Attack the function with the highest HIGH count first (per-function summary at the bottom of the report).

## Phase 4 — Classify survivors

Triage each surviving mutant into one of three buckets:

### High-value (always kill these)
- **Arithmetic / constant changes** (e.g., `* 1000` → `/ 1000`, `// 1000` → `// 1001`) — near-universally real bugs waiting to happen.
- **Comparison / boolean flips** (e.g., `==` → `!=`, `and` → `or`, `<` → `<=`).
- **Argument forwarding** (e.g., `f(access_token)` → `f(None)`) — exposes tests that never asserted their own mock was called correctly.
- **Default value changes** (e.g., `.get("items", [])` → `.get("items", None)`) — exposes missing edge-case tests for sparse payloads.
- **Short-circuit / early-return changes.**
- **Header / page-object string mutations** in `inertia/http.py` or `inertia/middleware.py` — the v3 protocol is wire-level; a mutated header name or field key is almost always a real defect.

### Low-value (accept as survivors)
- **Logger argument mutations**: `logger.debug("msg %s", x)` → `logger.debug(None, x)`, or swapping to `None` in any format-string argument. Killing these forces exact log-string assertions, which are brittle and **violate the project's parameterized-logging philosophy** (see `.claude/rules/main-rules.md`: "Use parameterized logging only").
- **Mutations on dead / unreachable code**: mutations of statements with no observable effect (e.g., a `dict.pop(key, None)` where `key` was never inserted). These cannot be killed by tests — only by removing the dead code, which requires source permission.

### Bug-candidate (STOP and report)
- Any mutation whose surviving form produces wrong behavior that the original *doesn't* produce — i.e., the surviving mutant is "more correct" than the original, or reveals a latent defect. Do not fix. Report to the user, describe the behavior, and wait for a decision.
- For v3 protocol surfaces: if the surviving mutant exposes a divergence from the spec or the Laravel `3.x` reference, stop and brief the user. The fix may need a `protocol-researcher` or `laravel-comparator` cross-check before any change.

## Phase 5 — Bug check before writing tests

Before writing any test, re-read the source for each high-value survivor and ask:
- Is the original line actually correct? Or does the mutation expose an asymmetry?
- Is the line reachable? If not, it's dead code — flag it, don't kill the mutant.
- For protocol code: does the original match the v3 spec / Laravel reference, or is the mutation actually closer to spec?
- Does the test file already have the right structure to assert on this behavior, or is a new test case needed?

If anything smells, write up findings and pause. Do not modify library source without explicit user permission.

## Phase 6 — Write tests

**Only modify files under `inertia/tests/`.** Project rules apply to every new test:
- Type-hint anything you add (`inertia/` ships PEP 561 typing).
- If you touch a logger call, keep parameterized logging (`logger.info("msg %s", value)`); never pre-format with f-strings.
- If you see `getLogger(__name__)` in code you read, change it to `getLogger("inertia_django_full_of_juice")` (per `.claude/rules/main-rules.md`).

Typical moves:

- **Argument forwarding**: add `mock.assert_called_once_with(<expected>)` on the relevant mock.
- **Missing-key edge case**: add a new test where the mocked request/response omits an optional key.
- **Header / page-object mutations**: assert exact header names and page-object keys via `response.headers["X-Inertia-..."]` or by parsing the JSON body — don't rely on substring matches.
- **Time-dependent arithmetic**: wrap the test in a `freezegun`-style decorator or patch `datetime.now`, then compute the expected value explicitly and assert exact equality.

Run the updated tests under the project's canonical runner. Pass `--noinput` because the conftest leaves the test DB on disk (`keepdb=True`) and Django's runner would otherwise hang on a drop-confirmation prompt:

```bash
docker compose run --remove-orphans --rm integration-tests \
  python manage.py test --noinput inertia.tests.test_<target>
```

All tests must pass before re-running mutmut.

## Phase 7 — Re-run and measure

```bash
docker compose run --remove-orphans --rm integration-tests \
  mutmut run "inertia.<target>*"
```

Compare killed / survived counts vs the previous run. Iterate Phase 3 → Phase 7 until only the accepted low-value survivors remain.

## Target score

Effective mutation score = `(killed + caught_by_type_check) / total`. Without a `type_check_command`, this collapses to `killed / total`.

| Score | Verdict |
|---|---|
| ≥ 90% | Excellent — likely over-engineered tests; diminishing returns |
| **80%–90%** | **Target band for `inertia/` modules** |
| 70%–80% | Acceptable if remaining survivors are logging-only |
| < 70% | Ship more tests |

## When to stop killing mutants

Stop when **all remaining survivors fall into these categories**:

1. Logger format-string / argument mutations (`logger.debug`, `logger.warning`, `logger.info`, etc.).
2. Mutations on provably unreachable or no-op code.
3. Mutations whose only kill would require asserting error messages / log messages verbatim.
4. Mutations that would require integration-level fixtures disproportionate to the defect risk.

Also stop and escalate if:
- You've written 3+ new test cases chasing one survivor cluster — likely a signal the code needs refactoring, not more tests. Report and wait.
- A surviving mutant appears to reveal a real defect — report and wait for a decision.
- A surviving mutant in `inertia/http.py` / `inertia/middleware.py` exposes a v3 protocol divergence — brief the user before changing anything.

## Quick command reference

> **Worktree sessions**: prepend `-p <unique-project-name>` to every `docker compose` command below (e.g. `docker compose -p inertia-mut-middleware run ...`). Reuse the exact same project name across all commands of a single session so state (volumes, DB, `integration-tests` container) is shared. In-place sessions can omit `-p`.

```bash
# First-time / fresh run (scope testing to the target module via the CLI glob)
docker compose run --remove-orphans --rm integration-tests \
  mutmut run "inertia.<target>*"

# Text summary of results
docker compose run --remove-orphans --rm integration-tests mutmut results

# Only surviving IDs
docker compose run --remove-orphans --rm integration-tests bash -c \
  'mutmut results 2>&1 | grep "survived"'

# Diff for a specific mutant
docker compose run --remove-orphans --rm integration-tests \
  mutmut show '<fully.qualified.mutant.id>'

# Interactive TUI (requires -it)
docker compose run --remove-orphans --rm -it integration-tests mutmut browse

# Bulk triage: classify survivors by mutation shape, per-function summary.
docker compose run --remove-orphans --rm integration-tests \
  python scripts/triage_mutmut_survivors.py --target <target>

# Run project tests under Django runner (sanity check before re-running mutmut).
# --noinput is required: the conftest's keepdb leaves the test DB on disk and
# the runner would otherwise hang on a drop-confirmation prompt.
docker compose run --remove-orphans --rm integration-tests \
  python manage.py test --noinput inertia.tests.test_<target>
```

## After the session — project SDLC hygiene

Before declaring the task done, follow `.claude/rules/main-rules.md`:

1. **Run the full library suite** to confirm no regression:
   ```bash
   docker compose run --remove-orphans --rm integration-tests
   ```
2. **Lint & format** (no need to re-run tests after):
   ```bash
   docker compose run --remove-orphans --rm lint-formatter
   ```
3. **CHANGELOG.md** — only update if `inertia/` *outside* `inertia/tests/` changed. A pure test-additions session does not touch the changelog.
4. **`sample_project/E2E_TESTING.md`** — update only if the work changed an observable v3 surface (headers, page-object fields, middleware behavior, prop kinds).
5. **Commit** with Conventional Commits, one concern per commit. A library fix and a sample-project tweak go in two separate commits even when discovered together.
6. **Do not edit `pyproject.toml`'s `version`** by hand. The publish workflow runs `poetry version $TAG_NAME` from the tag.

## Cleanup (in-place sessions only)

In a worktree session you can just delete the worktree. In an in-place session, revert the transient state before committing:

```bash
docker compose run --remove-orphans --rm integration-tests bash -c 'rm -rf mutants mutants.sqlite'
# Then manually remove the [tool.mutmut] block from pyproject.toml and the
# root conftest.py if you don't want to keep them around.
```

## Deliverable per session

At the end of a mutation-testing session, report:
- Before/after counts (killed, survived, type-caught) and effective score.
- Table of which specific mutants were killed and by which new assertion.
- List of surviving mutants with justification (all should fall into the accept-as-survivor buckets).
- Any bug findings or dead-code observations — **explicitly flagged, not acted on**.
