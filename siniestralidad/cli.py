"""CLI aislada; no modifica el API ni el modelo aprobado en MLflow.

Ejemplos:
 python -m siniestralidad.cli entrenar --datos entregas/entrega_final/dataset_modelado_2017_2025.csv
 python -m siniestralidad.cli pronosticar --datos entregas/entrega_final/dataset_modelado_2017_2025.csv --modelo models:/DSA-Siniestralidad-Bogota-Offset/2 --tracking-uri http://127.0.0.1:8050
"""
import argparse
import json
from pathlib import Path

import numpy as np

from .entrenamiento import entrenar_candidato, guardar_reporte
from .features import cargar_dataset_modelado, construir_siguiente_mes
from .modelo import VARIABLES_OFFSET


def main(argv=None):
    p = argparse.ArgumentParser(description="Pipeline V2 sin promoción automática.")
    sub = p.add_subparsers(dest="comando", required=True)
    train = sub.add_parser("entrenar", help="Evaluar candidato contra 2024.")
    train.add_argument("--datos", required=True)
    train.add_argument("--registrar", action="store_true", help="Registrar solo como candidato.")
    train.add_argument("--tracking-uri")
    train.add_argument("--reporte", default="resultados_pipeline/metricas_v2.json")

    pred = sub.add_parser("pronosticar", help="Pronosticar el mes siguiente al último observado.")
    pred.add_argument("--datos", required=True)
    pred.add_argument("--modelo", required=True, help="URI del modelo MLflow aprobado.")
    pred.add_argument("--tracking-uri", required=True)
    pred.add_argument("--salida", default="resultados_pipeline/proyeccion_siguiente_mes.csv")

    args = p.parse_args(argv)
    if args.comando == "entrenar":
        _, metricas = entrenar_candidato(args.datos, registrar=args.registrar,
                                         tracking_uri=args.tracking_uri)
        guardar_reporte(metricas, args.reporte)
        print(json.dumps(metricas, ensure_ascii=False, indent=2))
        print("Reporte:", args.reporte)
        print("Ninguna versión fue promovida.")
    else:
        import mlflow
        import mlflow.pyfunc
        mlflow.set_tracking_uri(args.tracking_uri)
        panel = cargar_dataset_modelado(args.datos)
        siguiente = construir_siguiente_mes(panel)
        modelo = mlflow.pyfunc.load_model(args.modelo)
        esquema = modelo.metadata.get_input_schema()
        columnas = esquema.input_names() if esquema is not None else list(VARIABLES_OFFSET)
        predicciones = np.asarray(modelo.predict(siguiente[columnas]), dtype=float)
        if not np.isfinite(predicciones).all() or (predicciones < 0).any():
            raise ValueError("El modelo produjo predicciones inválidas.")
        salida = siguiente[["LOCALIDAD", "PERIODO", "MEDIA_MOVIL_12", "LAG_12"]].copy()
        salida["PREDICCION"] = predicciones
        salida["MODELO_URI"] = args.modelo
        ruta = Path(args.salida)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        salida.to_csv(ruta, index=False, encoding="utf-8-sig")
        print(f"Proyección de {salida['PERIODO'].iloc[0]:%Y-%m}, {len(salida)} localidades")
        print(salida.to_string(index=False))
        print("Salida:", ruta)


if __name__ == "__main__":
    main()
