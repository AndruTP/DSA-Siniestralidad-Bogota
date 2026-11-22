"""Extracción fiel de la clase ModeloOffset del notebook V2 (celda 45).

El modelo registrado en MLflow no cambia al incorporar este módulo: solo se
utiliza en nuevos entrenamientos. No se promueve ninguna versión automáticamente.
"""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.linear_model import PoissonRegressor
from sklearn.ensemble import HistGradientBoostingRegressor

VARIABLES_OFFSET = (
    "MES_SIN", "MES_COS", "LAG_1", "LAG_3", "LAG_6", "LAG_12",
    "MEDIA_MOVIL_3", "MEDIA_MOVIL_6", "MEDIA_MOVIL_12",
    "EWM_6", "ESTACIONAL_CIUDAD", "PERIODO_2020_2021",
)
REZAGOS_OFFSET = (
    "LAG_1", "LAG_3", "LAG_6", "LAG_12",
    "MEDIA_MOVIL_3", "MEDIA_MOVIL_6", "EWM_6",
)
# Configuración «Menor complejidad», notebook V2, celda 68.
CONFIG_V2 = dict(tipo="ensamble", alpha_glm=0.001, max_iter=200,
                 learning_rate=0.03, max_leaf_nodes=6, min_samples_leaf=40)


class ModeloOffset(BaseEstimator, RegressorMixin):
    """GLM Poisson y/o Gradient Boosting Poisson sobre SINIESTROS / MM12."""

    def __init__(self, tipo="ensamble", alpha_glm=1e-3, max_iter=300,
                 learning_rate=0.03, max_leaf_nodes=8, min_samples_leaf=30):
        self.tipo = tipo
        self.alpha_glm = alpha_glm
        self.max_iter = max_iter
        self.learning_rate = learning_rate
        self.max_leaf_nodes = max_leaf_nodes
        self.min_samples_leaf = min_samples_leaf

    def _matriz(self, X):
        Z = pd.DataFrame(
            {c: np.log1p(X[c]) - np.log1p(X["MEDIA_MOVIL_12"])
             for c in REZAGOS_OFFSET},
            index=X.index,
        )
        Z["MES_SIN"] = X["MES_SIN"]
        Z["MES_COS"] = X["MES_COS"]
        Z["PERIODO_2020_2021"] = X["PERIODO_2020_2021"]
        Z["ESTACIONAL_CIUDAD"] = np.log(
            X["ESTACIONAL_CIUDAD"].clip(lower=1e-8)
        )
        return Z

    def fit(self, X, y):
        nivel = X["MEDIA_MOVIL_12"].clip(lower=1).to_numpy()
        Z = self._matriz(X)
        razon = np.asarray(y) / nivel

        self.glm_ = PoissonRegressor(alpha=self.alpha_glm, max_iter=5000)
        self.glm_.fit(Z, razon, sample_weight=nivel)

        self.hgb_ = HistGradientBoostingRegressor(
            loss="poisson", max_iter=self.max_iter,
            learning_rate=self.learning_rate,
            max_leaf_nodes=self.max_leaf_nodes,
            min_samples_leaf=self.min_samples_leaf,
            random_state=42,
        )
        self.hgb_.fit(Z, razon, sample_weight=nivel)
        return self

    def predict(self, X):
        nivel = X["MEDIA_MOVIL_12"].clip(lower=1).to_numpy()
        Z = self._matriz(X)
        razon_glm = self.glm_.predict(Z)
        razon_hgb = self.hgb_.predict(Z)
        if self.tipo == "glm":
            razon = razon_glm
        elif self.tipo == "hgb":
            razon = razon_hgb
        elif self.tipo == "ensamble":
            razon = (razon_glm + razon_hgb) / 2
        else:
            raise ValueError(f"Tipo de modelo no reconocido: {self.tipo}")
        return razon * nivel
