# =============================================================================
# calibrate_model.py - calibrates the trained model's probabilities
# =============================================================================
#
# WHAT changed compared to the original lab
#
# WHAT CALIBRATION IS
# -------------------
# A model can be accurate but still give misleading probabilities. For
# example, it might say "95% malignant" for cases that turn out malignant
# only 85% of the time. Calibration corrects the probabilities so that
# "80%" really means right about 80% of the time.
#
# HOW IT WORKS HERE
# -----------------
# 1. Load the model saved by train_model.py.
# 2. Wrap it in FrozenEstimator, so the model itself is NOT retrained or
#    changed in any way.
# 3. The frozen model makes predictions on the calibration split (rows it
#    did not train on). CalibratedClassifierCV fits a small calibrator that
#    learns how to map those predicted probabilities to the true labels.
# 4. Save the model + calibrator together as a new file, next to the
#    original. Both versions are kept, so evaluate_model.py can compare
#    them before and after calibration.
#
# Two methods are available (--method):
#   sigmoid  -> Platt scaling: fits a smooth S-shaped curve. Works well on
#               small data like ours (114 calibration rows). Default.
#   isotonic -> isotonic regression: fits a flexible step-shaped curve.
#               More powerful, but can overfit when data is small.
# The workflows let you choose the method when running them manually.

import argparse

from joblib import dump, load
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

from dataset import load_splits


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timestamp", type=str, required=True,
                        help="Version id of the trained model to calibrate")
    parser.add_argument("--method", choices=["sigmoid", "isotonic"], default="sigmoid",
                        help="sigmoid = Platt scaling, isotonic = isotonic regression")
    args = parser.parse_args()

    model = load(f"models/model_{args.timestamp}_gb.joblib")

    # Only the calibration split is used here
    _, X_cal, _, _, y_cal, _ = load_splits()

    # FrozenEstimator: keep the trained model as-is, only fit the calibrator
    calibrated = CalibratedClassifierCV(FrozenEstimator(model), method=args.method)
    calibrated.fit(X_cal, y_cal)

    out_path = f"models/model_{args.timestamp}_gb_calibrated.joblib"
    dump(calibrated, out_path)
    print(f"Calibrated with {args.method}; saved to {out_path}")