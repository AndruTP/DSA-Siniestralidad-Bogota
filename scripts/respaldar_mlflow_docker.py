"""Clona backend y artefactos locales del MLflow host para Compose en EC2.

No detiene MLflow ni altera la DB original. Copia SQLite con el método backup,
no con cp, para preservar una instantánea coherente.
"""
import argparse
import shutil
import sqlite3
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--origen", default="/home/ubuntu")
    p.add_argument("--destino", default="runtime/mlflow-docker")
    a = p.parse_args()
    home, out = Path(a.origen).resolve(), Path(a.destino).resolve()
    original = home / "mlflow.db"
    if not original.is_file():
        raise SystemExit("No existe /home/ubuntu/mlflow.db. No crear una DB vacía.")
    out.mkdir(parents=True, exist_ok=True)
    destino_db = out / "mlflow.db"
    if destino_db.exists():
        raise SystemExit("El respaldo ya existe; no se sobreescribe automáticamente.")
    origen_db = sqlite3.connect(f"file:{original}?mode=ro", uri=True)
    copia_db = sqlite3.connect(destino_db)
    try:
        origen_db.backup(copia_db)
    finally:
        copia_db.close()
        origen_db.close()
    print("SQLite respaldado:", destino_db)
    for nombre in ("mlartifacts", "mlruns"):
        src, dst = home / nombre, out / nombre
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
            print("Artefactos respaldados:", dst)
        else:
            dst.mkdir(exist_ok=True)
            print("Sin directorio en home:", src)
    print("No se ha sustituido el servicio MLflow host.")
    print("Si los modelos del Registry usan rutas de artefactos externas a home,")
    print("deben migrarse esas ubicaciones antes de usar la copia en producción.")


if __name__ == "__main__":
    main()
