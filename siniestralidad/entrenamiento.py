"""Entrenamiento y evaluación temporal de candidatos V2 (sin promoción automática)."""
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

from .features import cargar_dataset_modelado, agregar_caracteristicas_v2
from .modelo import ModeloOffset, VARIABLES_OFFSET, CONFIG_V2


def calcular_metricas(reales, pred):
    a, b = np.asarray(reales), np.asarray(pred)
    if len(a) != len(b) or len(a) == 0 or not np.isfinite(b).all():
        raise ValueError("Predicciones inválidas.")
    return {
        "mae": float(mean_absolute_error(a, b)),
        "rmse": float(np.sqrt(mean_squared_error(a, b))),
        "sesgo": float(np.mean(b - a)),
    }


def entrenar_candidato(ruta_dataset, *, registrar=False,
                       tracking_uri=None, experimento="siniestralidad-v2-candidatos"):
    """Reproduce la evaluación 2017–23 → 2024 con configuración V2 congelada.

    NO utiliza el test 2025; NO registra/promueve en Model Registry.
    La preparación del archivo original ACCIDENTE.csv se implementará aparte.
    """
    panel = cargar_dataset_modelado(ruta_dataset)
    extendido = agregar_caracteristicas_v2(panel)
    train = extendido.loc[extendido["ANIO"].between(2017, 2023)].copy()
    val = extendido.loc[extendido["ANIO"].eq(2024)].copy()
    test = extendido.loc[extendido["ANIO"].eq(2025)].copy()
    if train["ANIO"].nunique() != 7 or val["MES"].nunique() != 12 or len(test) != len(val):
        raise ValueError("El conjunto no permite reproducir la validación V2 2017–2024.")
    if train["PERIODO"].max() >= val["PERIODO"].min() or val["PERIODO"].max() >= test["PERIODO"].min():
        raise ValueError("Las particiones se superponen.")
    config = dict(CONFIG_V2)
    modelo = ModeloOffset(**config)
    modelo.fit(train[list(VARIABLES_OFFSET)], train["SINIESTROS"])
    pred = modelo.predict(val[list(VARIABLES_OFFSET)])
    m = calcular_metricas(val["SINIESTROS"], pred)
    base = calcular_metricas(val["SINIESTROS"], val["MEDIA_MOVIL_12"])
    m["mae_base_mm12"] = base["mae"]
    m["mejora_vs_base_pct"] = 100 * (base["mae"] - m["mae"]) / base["mae"]
    m["entrenamiento"] = "2017-2023"
    m["validacion"] = "2024"
    m["test_2025"] = "reservado"
    m["filas_entrenamiento"] = len(train)
    m["filas_validacion"] = len(val)
    m["filas_test_no_evaluado"] = len(test)
    m["dataset_sha256"] = hashlib.sha256(Path(ruta_dataset).read_bytes()).hexdigest()
    m["estado"] = "candidato_no_aprobado"

    if registrar:
        if not tracking_uri:
            raise ValueError("Para registrar se requiere --tracking-uri explícito.")
        import mlflow
        import mlflow.sklearn
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experimento)
        with mlflow.start_run(run_name="candidato-offset-v2-menor-complejidad") as run:
            mlflow.log_params(config)
            mlflow.set_tags({
                "proyecto": "siniestralidad-bogota",
                "estado": "candidato_no_aprobado",
                "dataset_sha256": m["dataset_sha256"],
                "test_2025": "reservado",
                "origen": "pipeline_v2_extraido",
            })
            mlflow.log_metrics({
                "mae_val_2024": m["mae"],
                "rmse_val_2024": m["rmse"],
                "sesgo_val_2024": m["sesgo"],
                "mae_base_mm12_2024": m["mae_base_mm12"],
                "mejora_vs_base_pct": m["mejora_vs_base_pct"],
            })
            mlflow.sklearn.log_model(
                sk_model=modelo, name="modelo", serialization_format="cloudpickle"
            )
            m["mlflow_run_id"] = run.info.run_id
    return modelo, m


def guardar_reporte(metricas, ruta_salida):
    ruta = Path(ruta_salida)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(metricas, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return ruta
