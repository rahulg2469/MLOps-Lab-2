
# WHAT changed compared to the original lab
# 1. Proper test data: the original made a NEW random synthetic dataset
#    (0-2000 rows, could be 0) to evaluate on. Now it uses the fixed test
#    split from dataset.py, which neither the model nor the calibrator
#    learned from, and which is identical in every run.
# 2. Before vs after calibration: it scores both the raw model and the
#    calibrated model, so you can see what calibration changed.
# 3. More metrics: the original only reported F1. Now:
#      f1, accuracy -> how often the yes/no prediction is right
#      brier        -> how good the probabilities are (lower is better)
#      log_loss     -> also probability quality, punishes confident
#                      mistakes harder (lower is better)
#    Brier and log loss are the metrics calibration is meant to improve.
# 4. Quality gate (new): if the calibrated model's F1 is below --min-f1
#    (default 0.90), the script exits with an error. In GitHub Actions this
#    turns the step red, stops the workflow, and nothing gets committed.
# 5. GitHub Actions integration (new):
#      - writes a metrics table to $GITHUB_STEP_SUMMARY, so it shows up on
#        the run's Summary page
#      - writes promote=true/false to $GITHUB_OUTPUT, which the nightly
#        workflow reads to decide whether to commit
#    Locally these variables don't exist, so the script just prints.


import argparse
import glob
import json
import os
import sys

from joblib import load
from sklearn.metrics import accuracy_score, brier_score_loss, f1_score, log_loss

from dataset import load_splits


def score(model, X, y):
    proba = model.predict_proba(X)[:, 1]  # predicted probability of malignant
    pred = (proba >= 0.5).astype(int)     # yes/no prediction
    return {
        "f1": round(f1_score(y, pred), 4),
        "accuracy": round(accuracy_score(y, pred), 4),
        "brier": round(brier_score_loss(y, proba), 4),
        "log_loss": round(log_loss(y, proba), 4),
    }


def latest_previous_metrics():
    """Metrics of the most recently committed model (the current champion), if any.
    Files are named <timestamp>_metrics.json, so sorting by name sorts by time."""
    files = sorted(glob.glob("metrics/*_metrics.json"))
    for path in reversed(files):
        with open(path) as f:
            data = json.load(f)
        if "calibrated" in data:  # skip files in an older format
            return data
    return None


def write_github_file(env_var, text):
    """Append to a GitHub Actions file ($GITHUB_STEP_SUMMARY / $GITHUB_OUTPUT).
    Does nothing when run locally, where these variables are not set."""
    path = os.environ.get(env_var)
    if path:
        with open(path, "a") as f:
            f.write(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timestamp", type=str, required=True,
                        help="Version id of the model to evaluate")
    parser.add_argument("--min-f1", type=float, default=0.90,
                        help="Quality gate: minimum F1 of the calibrated model on the test set")
    parser.add_argument("--compare-latest", action="store_true",
                        help="Only promote if calibrated Brier beats the current champion")
    args = parser.parse_args()

    raw = load(f"models/model_{args.timestamp}_gb.joblib")
    calibrated = load(f"models/model_{args.timestamp}_gb_calibrated.joblib")

    # Only the test split is used here
    _, _, X_test, _, _, y_test = load_splits()

    # Read the current champion BEFORE writing this run's metrics file
    previous = latest_previous_metrics()

    params = raw.get_params()
    metrics = {
        "timestamp": args.timestamp,
        "hyperparameters": {k: params[k] for k in ("n_estimators", "learning_rate", "max_depth")},
        "uncalibrated": score(raw, X_test, y_test),
        "calibrated": score(calibrated, X_test, y_test),
    }

    os.makedirs("metrics", exist_ok=True)
    with open(f"metrics/{args.timestamp}_metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)

    # Quality gate
    gate_passed = metrics["calibrated"]["f1"] >= args.min_f1

    # Promotion decision
    if not args.compare_latest:
        promote = gate_passed
        reason = "push run: promoted if quality gate passes"
    elif previous is None:
        promote = gate_passed
        reason = "no previous model to compare against"
    else:
        prev_brier = previous["calibrated"]["brier"]
        new_brier = metrics["calibrated"]["brier"]
        promote = gate_passed and new_brier < prev_brier
        reason = f"new Brier {new_brier} vs current {prev_brier} (from {previous['timestamp']})"

    # Summary table (printed, and shown on the GitHub Actions run page)
    u, c = metrics["uncalibrated"], metrics["calibrated"]
    summary = [
        f"## Model {args.timestamp}",
        f"Hyperparameters: `{metrics['hyperparameters']}`",
        "",
        "| Metric | Uncalibrated | Calibrated |",
        "|---|---|---|",
    ]
    summary += [f"| {k} | {u[k]} | {c[k]} |" for k in u]
    summary += [
        "",
        f"Quality gate (F1 >= {args.min_f1}): **{'passed' if gate_passed else 'FAILED'}**",
        f"Promote: **{promote}** ({reason})",
        "",
    ]
    summary_text = "\n".join(summary)
    print(summary_text)
    write_github_file("GITHUB_STEP_SUMMARY", summary_text)
    write_github_file("GITHUB_OUTPUT", f"promote={'true' if promote else 'false'}\n")

    # Push runs: a failed gate fails the step (and the workflow), so a code
    # change that produces a bad model shows up as a red run.
    # Nightly runs (--compare-latest): a failed gate just rejects this
    # candidate (promote=false, nothing committed) and the run stays green.
    if not gate_passed:
        print(f"Quality gate failed: calibrated F1 {c['f1']} < {args.min_f1}")
        if not args.compare_latest:
            sys.exit(1)