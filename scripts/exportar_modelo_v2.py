"""Copia local del modelo aprobado para inferencia Docker, sin reentrenar ni promover.

Se ejecuta EN EC2 con el MLflow original levantado; nunca copia credenciales.
"""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import mlflow
import mlflow.artifacts
import mlflow.pyfunc

DEFAULT_MODEL = "models:/DSA-Siniestralidad-Bogota-Offset/2"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for bloque in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Exportar modelo V2 a runtime/serving.")
    parser.add_argument("--tracking-uri", default="http://127.0.0.1:8050")
    parser.add_argument("--modelo", default=DEFAULT_MODEL)
    parser.add_argument("--destino", default="runtime/serving/modelo_v2")
    args = parser.parse_args()
    destino = Path(args.destino).resolve()
    if destino.exists():
        mlmodel = destino / "MLmodel"
        if not mlmodel.is_file():
            raise SystemExit("El destino existe pero no contiene MLmodel; revisar manualmente.")
        print("Modelo ya exportado en:", destino)
        print("SHA-256 MLmodel:", sha256(mlmodel))
        return

    mlflow.set_tracking_uri(args.tracking_uri)
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Separar la ruta de descarga y destino: no copiar un directorio dentro
    # de sí mismo si MLflow devuelve como ruta el propio dst_path.
    with tempfile.TemporaryDirectory(prefix=".modelo-v2-", dir=destino.parent) as tmp:
        tmpdir = Path(tmp)
        descarga = tmpdir / "descarga"
        descarga.mkdir()
        descargado = Path(mlflow.artifacts.download_artifacts(
            artifact_uri=args.modelo, dst_path=str(descarga)
        ))
        if not (descargado / "MLmodel").is_file():
            raise RuntimeError("El Registry no devolvió un directorio de modelo MLflow.")
        temporal = tmpdir / "modelo-validado"
        shutil.copytree(descargado, temporal)
        # Verificar que el modelo exportado se carga antes de activar su copia.
        comprobado = mlflow.pyfunc.load_model(str(temporal))
        if comprobado.metadata.get_input_schema() is None:
            raise RuntimeError("Modelo sin esquema de entradas.")
        manifiesto = {
            "uri_registro": args.modelo,
            "tracking_origen": args.tracking_uri,
            "sha256_mlmodel": sha256(temporal / "MLmodel"),
            "tipo": "copia_aprobada_para_inferencia",
            "reentrenado": False,
        }
        (temporal / "manifest_dsa.json").write_text(
            json.dumps(manifiesto, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporal.rename(destino)
    print("Exportación realizada:", destino)
    print("Modelo MLflow aprobado:", args.modelo)
    print("No se modificó el registro ni se ejecutó entrenamiento.")


if __name__ == "__main__":
    main()
