# Lab 1: Automated Testing with GitHub Actions

**Course:** MLOps (IE-7374) · **Author:** Rahul Gudivada

**Original lab:** this lab is based on [Labs/Github_Labs/Lab1](https://github.com/raminmohammadi/MLOps/tree/main/Labs/Github_Labs/Lab1) from the course repository [raminmohammadi/MLOps](https://github.com/raminmohammadi/MLOps). Section 1 lists everything I changed compared to that version.

This lab is built on a small calculator module (`src/calculator.py`). The point isn't the math. It's the **automated testing pipeline** around the code: every push or pull request is style-checked, tested on three Python versions, and blocked if test coverage drops.

The original lab had two separate GitHub Actions workflows that ran a few hard-coded tests on Python 3.8. I replaced them with a single CI pipeline that has a lint stage, a Python version matrix, a coverage gate, saved reports, and a results summary. I also moved the test cases into a CSV file in `data/`.

---

## Table of contents
1. [What I changed](#1-what-i-changed)
2. [Project structure](#2-project-structure)
3. [Prerequisites](#3-prerequisites-what-to-install)
4. [Setup](#4-setup)
5. [Running locally](#5-running-the-lab-locally)
6. [Running on GitHub Actions](#6-running-the-pipeline-on-github-actions)
7. [What a successful run looks like](#7-what-a-successful-run-looks-like)
8. [Try it: see the pipeline catch problems](#8-try-it-see-the-pipeline-catch-problems)
9. [Adding a new test case](#9-adding-a-new-test-case)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. What I changed

### Summary: original vs. modified

| Area | Original lab | My version |
|---|---|---|
| Workflows | Two separate files (`github_lab1_pytest_action.yml`, `github_lab2_unittest_action.yml`) | One combined workflow: `.github/workflows/lab1_ci.yml` |
| Triggers | Push to `main` only | Push **and** pull requests to `main`, manual run button, and a path filter (runs only when Lab1 files change) |
| Pipeline stages | Tests only | **Lint → Test** (tests run only if lint passes) |
| Python versions | 3.8 only (end-of-life) | **3.10, 3.11, 3.12** in parallel (matrix) |
| `setup-python` | v4, no caching | v5 with built-in pip caching |
| Code quality | None | `flake8` lint stage |
| Coverage | Not measured | `pytest-cov` with a **90% coverage gate** (the build fails below it) |
| Reports | One JUnit XML artifact | JUnit and coverage XML for **each** Python version, with unique artifact names |
| Results visibility | Echo messages in logs | A **results table** on the run's Summary page |
| Overlapping runs | All run | A newer push cancels the older run on the same branch |
| Test cases | Hard-coded `assert`s | Loaded from `data/test_cases.csv`, shared by pytest and unittest |
| Error tests | None | Tests for invalid inputs (`ValueError`) and division by zero |
| `calculator.py` | `fun4` had no input validation | Shared validation helper for all functions, plus a new `fun5` (divide) |
| Dependencies | `pytest` (unpinned) | Pinned `pytest`, `pytest-cov`, `flake8` |

### The changes in detail

#### A. CI/CD pipeline (the main change): `.github/workflows/lab1_ci.yml`

1. **One workflow, two jobs, chained with `needs:`**
   - `lint` runs `flake8` on `src/` and `test/`.
   - `test` runs only if `lint` passes (`needs: lint`). Badly formatted code never reaches the test stage, which saves runner time and gives faster feedback.

2. **Matrix build across Python versions.** The `test` job runs three times in parallel, on Python 3.10, 3.11 and 3.12. This catches version-specific bugs, and it replaces Python 3.8, which is end-of-life and no longer supported. `fail-fast: false` lets every version finish, so you can see exactly which versions failed.

3. **Coverage gate.** Pytest runs with `--cov=src --cov-fail-under=90`. If tests cover less than 90% of the code in `src/`, the job fails. Untested code can't slip into `main`.

4. **Both test frameworks in every matrix run.** pytest and unittest run on every Python version, instead of each living in its own workflow.

5. **Artifacts for each Python version.** `pytest-report.xml` (JUnit) and `coverage.xml` are uploaded as `test-reports-py3.10`, `test-reports-py3.11` and `test-reports-py3.12`. The names have to be unique, because `upload-artifact@v4` fails when a matrix tries to upload two artifacts with the same name. The upload uses `if: always()`, so reports are saved even when the tests fail. That's exactly when you need them.

6. **Job summary.** A small Python script reads the JUnit and coverage XML files and writes a Markdown table to `$GITHUB_STEP_SUMMARY`. The table shows the test count, passes and failures, coverage percentage, and threshold for each Python version on the run's Summary page, so you don't have to dig through logs.

7. **Better triggers.**
   - `pull_request`: tests run *before* code is merged, which is the core idea of CI.
   - `workflow_dispatch`: adds a **Run workflow** button for manual runs.
   - `paths:` filter: the workflow only runs when files in `Labs/Github_Labs/Lab1/` (or the workflow itself) change, so other labs in the repo don't trigger it.

8. **Concurrency control.** `concurrency: group: lab1-ci-${{ github.ref }}` with `cancel-in-progress: true`. If you push twice quickly, the outdated run is cancelled.

9. **Updated actions.** `actions/setup-python` moved from v4 to v5, using its built-in pip cache (`cache: pip`), keyed on `requirements.txt`.

#### B. Data-driven tests: `data/test_cases.csv`

The original `data/` folder was empty. It now holds 22 test cases in this format:

```csv
function,x,y,z,expected
fun1,2,3,,5
fun4,2,3,5,10
fun5,7,2,,3.5
```

- **pytest** loads the CSV and feeds every row into one test with `@pytest.mark.parametrize`. Each row shows up as its own test, e.g. `test_calculator_from_csv[fun1(2, 3)]`.
- **unittest** reads the same CSV and checks each row inside `self.subTest(...)`, so one bad row doesn't hide the others.
- Adding a test case means adding a CSV row. No code changes are needed.

Pytest also checks that the CSV covers all five functions, so a function can't silently lose its tests.

#### C. Code changes: `src/calculator.py`

- Added a shared `_check_numbers()` helper used by every function, replacing the copy-pasted checks.
- `fun4` (sum of three numbers) now validates its inputs. In the original, it was the only function without validation.
- Added `fun5(x, y)`, which divides and raises `ZeroDivisionError` when `y == 0`.

#### D. Error-handling tests

- pytest uses a parametrized `pytest.raises(ValueError)` test that sends bad inputs (`"a"`, `None`, `[1]`, `"3"`) to every function, plus a division-by-zero test.
- unittest has matching `assertRaises` tests.

These are what push coverage to **100%**, since the error branches are now tested too.

---

## 2. Project structure

```
<repo-root>/
├── .github/
│   └── workflows/
│       └── lab1_ci.yml          # NEW: combined CI pipeline (replaces the 2 old workflows)
└── Labs/Github_Labs/Lab1/
    ├── .flake8                  # NEW: lint config (max line length 100)
    ├── README.md                # this file
    ├── requirements.txt         # CHANGED: pinned pytest, pytest-cov, flake8
    ├── data/
    │   └── test_cases.csv       # NEW: test cases used by both test suites
    ├── src/
    │   ├── __init__.py
    │   └── calculator.py        # CHANGED: shared validation, fun4 validated, new fun5
    └── test/
        ├── __init__.py
        ├── test_pytest.py       # CHANGED: CSV-driven parametrized tests and error tests
        └── test_unittest.py     # CHANGED: CSV-driven subTests and error tests
```

> GitHub only reads workflows from `.github/workflows/` at the **repository root**, which is why the workflow file isn't inside the `Lab1` folder.

---

## 3. Prerequisites (what to install)

| Tool | Version | Why | Get it |
|---|---|---|---|
| **Git** | any recent version (2.30+) | clone the repo, commit and push | https://git-scm.com/downloads |
| **Python** | **3.10, 3.11 or 3.12** | runs the code and tests (3.8/3.9 aren't supported) | https://www.python.org/downloads/ |
| **GitHub account** | – | to run the pipeline on GitHub Actions | https://github.com |

Python packages are installed in step 4 from `requirements.txt`. These versions are pinned so everyone gets the same results:

| Package | Version | Purpose |
|---|---|---|
| `pytest` | 8.3.4 | test runner |
| `pytest-cov` | 6.0.0 | coverage measurement and coverage gate |
| `flake8` | 7.1.1 | style and lint checks |

**Windows users:** when installing Python, tick **"Add python.exe to PATH"**. Run the commands below in **Git Bash** (it comes with Git for Windows) or PowerShell.

Check your installs:
```bash
git --version
python --version     # must show 3.10.x, 3.11.x or 3.12.x (on some systems: python3 --version)
```

---

## 4. Setup

### 4.1 Get the code

```bash
git clone https://github.com/rahulg2469/MLOps-Lab-2.git
cd MLOps-Lab-2/Labs/Github_Labs/Lab1
```

### 4.2 Create and activate a virtual environment

A virtual environment keeps this lab's packages separate from the rest of your system.

```bash
python -m venv venv
```

Activate it:

| OS / shell | Command |
|---|---|
| macOS / Linux | `source venv/bin/activate` |
| Windows (Git Bash) | `source venv/Scripts/activate` |
| Windows (PowerShell) | `venv\Scripts\Activate.ps1` |
| Windows (cmd) | `venv\Scripts\activate.bat` |

Your prompt should now start with `(venv)`.

> Make sure `venv/` is listed in `.gitignore` so the virtual environment is never committed.

### 4.3 Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 5. Running the lab locally

Run all of these from `Labs/Github_Labs/Lab1/` with the virtual environment active. These are the same commands the pipeline runs.

### 5.1 Lint

```bash
flake8 src test
```
**Success:** no output at all.

### 5.2 Pytest with the coverage gate

```bash
python -m pytest test/test_pytest.py -v --cov=src --cov-report=term-missing --cov-fail-under=90
```
**Success** looks like this:
```
test/test_pytest.py::test_csv_covers_every_function PASSED
test/test_pytest.py::test_calculator_from_csv[fun1(2, 3)] PASSED
...
test/test_pytest.py::test_divide_by_zero PASSED

---------- coverage: ... ----------
Name                Stmts   Miss  Cover   Missing
-------------------------------------------------
src/__init__.py         0      0   100%
src/calculator.py      ..      0   100%
-------------------------------------------------
TOTAL                  ..      0   100%

Required test coverage of 90% reached. Total coverage: 100.00%
============================== 29 passed in ...s ==============================
```

The 29 tests are 22 CSV cases, 5 invalid-input cases, 1 divide-by-zero test and 1 CSV completeness check.

### 5.3 Unittest

```bash
python -m unittest test.test_unittest -v
```
**Success:**
```
test_cases_from_csv (test.test_unittest.TestCalculator...) ... ok
test_divide_by_zero (test.test_unittest.TestCalculator...) ... ok
test_invalid_inputs (test.test_unittest.TestCalculator...) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.00Xs

OK
```

> `test_cases_from_csv` checks all 22 CSV rows internally with `subTest`, so it counts as 1 test but covers every case.

---

## 6. Running the pipeline on GitHub Actions

### 6.1 One-time setup (forks only)

If you forked this repository, GitHub disables Actions on forks by default:

1. Open your fork on GitHub and click the **Actions** tab.
2. Click **"I understand my workflows, go ahead and enable them"**.
3. *(Optional)* The fork also has workflows for other labs (some need GCP secrets and will fail). To keep things clean, select each one in the left sidebar and choose **"..." → Disable workflow**. Leave **Lab1 CI - Lint, Test, Coverage** enabled.

No secrets are needed for this lab.

### 6.2 Trigger the pipeline

Any of these will start it:

- **Push a change** to any file under `Labs/Github_Labs/Lab1/` on `main`.
- **Open a pull request** into `main` that changes Lab1 files. The checks then appear on the PR.
- **Run it manually:** go to **Actions → Lab1 CI - Lint, Test, Coverage → Run workflow → Run workflow**.

A quick way to trigger it from the terminal:
```bash
git checkout -b test-ci
echo "" >> Labs/Github_Labs/Lab1/data/test_cases.csv   # tiny change inside Lab1
git commit -am "Trigger Lab1 CI"
git push -u origin test-ci
```
Then open a pull request from `test-ci` into `main` **in your own repository**. GitHub may default the base to the original repo, so check the base dropdown.

---

## 7. What a successful run looks like

In the **Actions** tab, open the latest **Lab1 CI - Lint, Test, Coverage** run.

**Jobs (left side), all with green checkmarks:**
```
lint  - passed
test (3.10)  - passed
test (3.11)  - passed
test (3.12)  - passed
```
The three `test` jobs start only after `lint` finishes, and they run in parallel.

**Summary page:** one table for each Python version:

| Metric | Value |
|---|---|
| Pytest tests | 29 |
| Passed | 29 |
| Failed | 0 |
| Coverage (src/) | 100.0% |
| Coverage threshold | 90% |

**Artifacts (bottom of the Summary page):**
- `test-reports-py3.10`
- `test-reports-py3.11`
- `test-reports-py3.12`

Each artifact contains `pytest-report.xml` and `coverage.xml`.

**On a pull request:** the four checks appear at the bottom of the PR as passing.

---

## 8. Try it: see the pipeline catch problems

These show that each gate actually works. Make the change, push it, watch the run fail, then revert it.

| Break this | Expected result |
|---|---|
| Add a line longer than 100 characters, or an unused `import os`, to `calculator.py` | `lint` fails, and the `test` jobs are **skipped** |
| Change a CSV row to a wrong answer, e.g. `fun1,2,3,,6` | All 3 `test` jobs fail. The failing test is named in the log, e.g. `test_calculator_from_csv[fun1(2, 3)]` |
| Delete `test_divide_by_zero` and the `fun5` error cases | Coverage drops. If it falls below 90%, the job fails with `FAIL Required test coverage of 90% not reached` |

You can do the same locally with the commands from section 5.

---

## 9. Adding a new test case

Open `data/test_cases.csv` and add a row:

```csv
fun3,4,2.5,,10.0
```

- Leave `z` empty for two-argument functions. Fill it in only for `fun4`.
- Use a decimal point (e.g. `10.0`) for float results. Float results are compared with a small tolerance.

Both pytest and unittest pick the new row up automatically. No code changes needed.

---

## 10. Troubleshooting

| Problem | Fix |
|---|---|
| `python: command not found` | Try `python3` (macOS/Linux) or `py` (Windows), or reinstall Python with "Add to PATH" ticked |
| `ModuleNotFoundError: No module named 'src'` | Run the commands from `Labs/Github_Labs/Lab1/`, and use `python -m pytest`, not plain `pytest` |
| `flake8: command not found` | The virtual environment isn't active. Activate it (section 4.2) and reinstall the requirements |
| PowerShell won't run `Activate.ps1` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use Git Bash |
| Workflow doesn't start after a push | Your change must touch `Labs/Github_Labs/Lab1/**` (path filter), and Actions must be enabled on your fork. Or use **Run workflow** |
| The old pytest/unittest workflows still run | Delete `github_lab1_pytest_action.yml` and `github_lab2_unittest_action.yml` from `.github/workflows/` |
| PR opened against the professor's repo by mistake | Close it and open a new PR with **base repository** set to your fork |
