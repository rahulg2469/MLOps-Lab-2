# Lab 2: Model Training, Calibration and Versioning with GitHub Actions

This lab uses GitHub Actions to automatically train a classifier, calibrate its predicted probabilities, evaluate it against a quality gate, and version the resulting model and metrics by committing them back to the repository.

## What the pipeline does

There are two workflows. GitHub only runs workflows from the repository root, so the active files are in `.github/workflows/`. Identical copies are kept in `Labs/Github_Labs/Lab2/workflows/` for reference.

**1. On push** (`github_lab2_model_calibration_on_push.yml`)

Runs when code in `Labs/Github_Labs/Lab2/src/`, `requirements.txt`, or the workflow file itself is pushed to `main`. It can also be started by hand.

Train -> Calibrate -> Evaluate + quality gate -> Commit model and metrics

**2. Nightly** (`github_lab2_model_calibration.yml`)

Runs every day at 05:00 UTC, and can also be started by hand. Each night it trains a model with a randomly sampled hyperparameter configuration, calibrates it, and compares it with the current model (the most recently committed one). It commits the new model only if it passes the quality gate and has a lower Brier score. Otherwise it commits nothing.

Train (random config) -> Calibrate -> Evaluate + compare with current model -> Commit only if better

## Dataset and model

- **Dataset:** Breast Cancer Wisconsin (bundled with scikit-learn, so nothing is downloaded). It has 569 samples, 30 numeric features, and binary labels. Labels are flipped so that 1 = malignant.
- **Split:** a fixed 60/20/20 train / calibration / test split (seed 42). Every run is scored on the same test set, so metrics are comparable across runs.
- **Model:** `GradientBoostingClassifier`.
- **Calibration:** `CalibratedClassifierCV` with sigmoid (Platt scaling, the default) or isotonic regression, fit on the calibration split. The trained model only makes predictions on these rows and never learns from them; the calibrator learns from those predictions how to correct the model's probabilities.
- **Metrics:** F1, accuracy, Brier score and log loss, each computed before and after calibration. Brier score and log loss measure how well the probabilities are calibrated; lower is better.

## Changes from the original lab

### Workflow changes

1. **Calibration actually happens now.** The original "calibration" workflows only retrained the model. There is now a dedicated calibration step (`src/calibrate_model.py`).
2. **Quality gate.** If the calibrated model's test F1 falls below a threshold (default 0.90), the run fails and nothing is committed.
3. **The nightly workflow has its own job.** It does a nightly hyperparameter search and promotes a new model only if it beats the current one on Brier score. Previously it duplicated the push workflow, and its paths pointed to `./src/...`, which does not exist in this repo, so it could not run.
4. **Manual runs with inputs.** Both workflows can be started from the Actions tab (`workflow_dispatch`), with a choice of calibration method (sigmoid / isotonic) and the F1 threshold.
5. **Run summary.** Each run posts a table of metrics before and after calibration, plus the gate and promotion decisions, on the run's summary page.
6. **Path filter on push.** The push workflow only runs when Lab 2 code changes, not on every push to the repo.

### Code changes

- Synthetic `make_classification` data replaced by the Breast Cancer dataset. The original could generate 0 samples and crash, because it used `random.randint(0, 2000)`.
- The model is no longer evaluated on its own training data. There is a proper held-out test set (`src/dataset.py`).
- RandomForest replaced by GradientBoosting, with optional random hyperparameters (`--search-seed`).
- `evaluate_model.py` now writes metrics into `metrics/`. Previously it created the folder but saved the file to the current directory.
- MLflow logging removed. Metrics are tracked in versioned JSON files in the repo and on the Actions summary page.
- Removed unused files: `src/test.ipynb` (leftover Lab 1 notebook) and the `test/` folder (it only held an empty `__init__.py`).
- Pinned dependency versions.
- The two Lab 1 test workflows were disabled in this fork's Actions tab, so only Lab 2 runs appear there.


## Running it on GitHub (no local install needed)

You only need a GitHub account.

1. Fork this repository.
2. In the fork, open the **Actions** tab and click "I understand my workflows, go ahead and enable them".
3. Optional: in the left sidebar, disable the two Lab 1 test workflows (open each one, "..." menu, **Disable workflow**) so only Lab 2 runs appear.
4. In the left sidebar, open **Lab 2 - Nightly Model Search and Calibration** and click **Enable workflow**. GitHub disables scheduled workflows in forks by default.
5. Start a run, using either option:
   - Open **Lab 2 - Train, Calibrate and Evaluate on Push**, click **Run workflow**, pick the options, then click **Run workflow** again.
   - Or push any change to a file in `Labs/Github_Labs/Lab2/src/`.
6. Do the same for the nightly workflow to test it without waiting for 05:00 UTC.

### What a successful run looks like

- Every step has a green check.
- The run's **Summary** page shows a table like this (exact numbers vary by run):

  | Metric | Uncalibrated | Calibrated |
  |---|---|---|
  | f1 | 0.95 | 0.9367 |
  | accuracy | 0.9649 | 0.9561 |
  | brier | 0.0337 | 0.0347 |
  | log_loss | 0.1381 | 0.1312 |

  followed by `Quality gate (F1 >= 0.9): passed` and the promotion decision.
- A new commit from `github-actions[bot]` appears on `main`. It adds `models/model_<ts>_gb.joblib`, `models/model_<ts>_gb_calibrated.joblib` and `metrics/<ts>_metrics.json` under `Labs/Github_Labs/Lab2/`.
- For the nightly workflow, a green run with "Promote: False" is also a success. It means the new model was not better, so the current model was kept and nothing was committed.

Note: calibration does not always improve every metric. With the default settings it lowers log loss but raises the Brier score slightly, because gradient boosting is already fairly well calibrated and the calibration set is small (114 rows). The pipeline measures this on every run instead of assuming calibration helped.

To see the quality gate fail: run the push workflow by hand with `min_f1` set to `0.99`. The evaluate step fails (red X) and no commit is made.

## Running it locally (optional)

**Requirements:**
- Git 2.x
- Python 3.11 (3.10 to 3.12 also work)

On Windows, use Git Bash for the commands below.

```bash
git clone https://github.com/<your-username>/MLOps-Lab-2.git
cd MLOps-Lab-2/Labs/Github_Labs/Lab2

python -m venv .venv
source .venv/bin/activate          # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt    # scikit-learn 1.6.1, numpy 2.2.6, joblib 1.4.2

# Push-workflow equivalent
python src/train_model.py --timestamp 20260101000000
python src/calibrate_model.py --timestamp 20260101000000 --method sigmoid
python src/evaluate_model.py --timestamp 20260101000000 --min-f1 0.90

# Nightly-workflow equivalent
python src/train_model.py --timestamp 20260102000000 --search-seed 20260102000000
python src/calibrate_model.py --timestamp 20260102000000
python src/evaluate_model.py --timestamp 20260102000000 --compare-latest
```

Each command prints what it did. The evaluate step prints the metrics table and the gate and promotion decisions. Models are saved to `models/` and metrics to `metrics/`.

Locally, every run writes a metrics file. In CI, a nightly run that is not promoted is never committed, so the "current model" comparison only sees promoted models.

## License

MIT, as in the original repository.