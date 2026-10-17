# =============================================================================
# dataset.py - loads the data and makes a fixed train / calibration / test split
# =============================================================================
#
# WHAT Changed compared to the original lab
# This file is new. In the original lab, train_model.py and evaluate_model.py
# each generated their own synthetic data with make_classification:
#   - n_samples=random.randint(0, 2000) could produce 0 rows and crash.
#   - The model was scored on the same data it was trained on, so the
#     reported F1 was close to meaningless.
#
# Now every script imports load_splits() from here, so they all see the
# same data split:
#   - Dataset: Breast Cancer Wisconsin, bundled with scikit-learn
#     (569 rows, 30 numeric features, binary label). Nothing is downloaded.
#   - Labels are flipped so 1 = malignant, the class we care about catching
#     (scikit-learn's default is 0 = malignant).
#   - Fixed 60/20/20 split with seed 42:
#       train       -> used by train_model.py. The model learns from this
#                      split only.
#       calibration -> used by calibrate_model.py. The trained model makes
#                      predictions on these rows (it does not learn from
#                      them). A separate calibrator compares those
#                      predictions with the true labels and learns how to
#                      correct the model's probabilities. We use separate
#                      rows because the model is overconfident on rows it
#                      trained on, which would hide the mistakes the
#                      calibrator needs to see.
#       test        -> used by evaluate_model.py. The model and calibrator
#                      only make predictions on it; nothing learns from it.
#   - stratify keeps the malignant/benign ratio the same in all three parts.
#   - The seed never changes, so every run (push or nightly) is scored on
#     the exact same test set. That is what lets the nightly workflow
#     compare a new model against the current one fairly.
# =============================================================================

from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split

SPLIT_SEED = 42


def load_splits():
    X, y = load_breast_cancer(return_X_y=True)
    y = 1 - y  # sklearn uses 0 = malignant; flip so 1 = malignant

    # 20% test set first, then split the remaining 80% into 60% train / 20% calibration
    X_rest, X_test, y_rest, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SPLIT_SEED
    )
    X_train, X_cal, y_train, y_cal = train_test_split(
        X_rest, y_rest, test_size=0.25, stratify=y_rest, random_state=SPLIT_SEED
    )
    return X_train, X_cal, X_test, y_train, y_cal, y_test


if __name__ == "__main__":
    X_train, X_cal, X_test, y_train, y_cal, y_test = load_splits()
    for name, X, y in [("train", X_train, y_train),
                       ("calibration", X_cal, y_cal),
                       ("test", X_test, y_test)]:
        print(f"{name:<12} {X.shape[0]:>3} rows, {X.shape[1]} features, {int(y.sum())} malignant")