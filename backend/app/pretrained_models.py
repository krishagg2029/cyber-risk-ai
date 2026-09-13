from __future__ import annotations
import os
import numpy as np
import pandas as pd

class PretrainedTabularRiskModel:
    """
    Uses TabPFN as the pretrained tabular foundation model.

    Important:
    - No model is trained from scratch.
    - TabPFN is pretrained.
    - The estimator API may perform inference-time dataset conditioning/fitting.
    - If you require absolutely no fitting/conditioning on your uploaded data,
      use a hosted pretrained inference service instead.
    """
    def __init__(self):
        self.available = False
        self.error = None
        try:
            from tabpfn import TabPFNClassifier, TabPFNRegressor
            self.TabPFNClassifier = TabPFNClassifier
            self.TabPFNRegressor = TabPFNRegressor
            self.available = True
        except Exception as exc:
            self.error = str(exc)

    def classify(self, features: pd.DataFrame, labels: pd.Series, x_new: pd.DataFrame):
        if not self.available:
            return None
        try:
            # Reference labels come from historical incident data.
            y = pd.to_numeric(labels, errors="coerce")
            valid = y.notna()
            X = features.loc[valid]
            y = y.loc[valid].astype(int)
            if len(X) < 2 or y.nunique() < 2:
                return None
            clf = self.TabPFNClassifier()
            clf.fit(X, y)
            proba = clf.predict_proba(x_new)[0]
            classes = list(clf.classes_)
            if 1 in classes:
                return float(proba[classes.index(1)])
            return float(proba[-1])
        except Exception as exc:
            self.error = str(exc)
            return None

    def regress(self, features: pd.DataFrame, labels: pd.Series, x_new: pd.DataFrame):
        if not self.available:
            return None
        try:
            y = pd.to_numeric(labels, errors="coerce")
            valid = y.notna()
            X = features.loc[valid]
            y = y.loc[valid]
            reg = self.TabPFNRegressor()
            reg.fit(X, y)
            pred = reg.predict(x_new)[0]
            return float(max(0, pred))
        except Exception as exc:
            self.error = str(exc)
            return None
