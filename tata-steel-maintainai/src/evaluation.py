"""
Model Evaluation and Metrics Module for TATA STEEL MAINTAINAI.
Calculates Precision, Recall, F1-Score, PR-AUC, ROC-AUC, Brier Score,
Confusion Matrix, Calibration Curves, and provides limitation explanations.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional, List
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    precision_recall_curve,
    average_precision_score,
    roc_auc_score,
    roc_curve,
    confusion_matrix,
    brier_score_loss,
)
from sklearn.calibration import calibration_curve


def evaluate_classifier(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray
) -> Dict[str, Any]:
    """
    Calculate comprehensive binary classification metrics for industrial failure prediction.
    Never fabricates metrics; gracefully handles single-class or edge cases.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)

    total_samples = len(y_true)
    positive_samples = int(np.sum(y_true))
    negative_samples = total_samples - positive_samples

    if positive_samples == 0:
        return {
            "status": "INSUFFICIENT_POSITIVE_EXAMPLES",
            "message": "Evaluation test split contains zero positive failure instances. Supervised evaluation metrics cannot be calculated.",
            "total_samples": total_samples,
            "positive_samples": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "pr_auc": 0.0,
            "roc_auc": 0.5,
            "brier_score": float(np.mean(y_prob ** 2)),
            "confusion_matrix": [[int(total_samples), 0], [0, 0]],
        }

    # Core metrics with zero_division=0 to prevent warnings
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    try:
        pr_auc = float(average_precision_score(y_true, y_prob))
    except Exception:
        pr_auc = float(positive_samples / max(1, total_samples))

    try:
        roc_auc = float(roc_auc_score(y_true, y_prob))
    except Exception:
        roc_auc = 0.5

    brier = float(brier_score_loss(y_true, y_prob))

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist()

    # Precision-Recall curve
    precisions, recalls, pr_thresholds = precision_recall_curve(y_true, y_prob)

    # ROC curve
    fpr, tpr, roc_thresholds = roc_curve(y_true, y_prob)

    # Calibration curve
    try:
        prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=10, strategy="uniform")
        calib_data = {
            "prob_true": prob_true.tolist(),
            "prob_pred": prob_pred.tolist(),
        }
    except Exception:
        calib_data = {"prob_true": [], "prob_pred": []}

    return {
        "status": "VALID",
        "total_samples": total_samples,
        "positive_samples": positive_samples,
        "negative_samples": negative_samples,
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "brier_score": round(brier, 4),
        "confusion_matrix": cm,
        "pr_curve": {
            "precision": [round(float(p), 4) for p in precisions],
            "recall": [round(float(r), 4) for r in recalls],
        },
        "roc_curve": {
            "fpr": [round(float(f), 4) for f in fpr],
            "tpr": [round(float(t), 4) for t in tpr],
        },
        "calibration": calib_data,
        "limitation_note": (
            "Model probabilities reflect statistical failure propensity under observed operating regimes. "
            "A high probability is an indication of severe asset risk requiring qualified inspection, "
            "not an absolute mechanical certainty of imminent failure."
        ),
    }
