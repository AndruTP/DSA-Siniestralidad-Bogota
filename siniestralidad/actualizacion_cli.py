"""CLI de prevalidación de un ACCIDENTE.csv acumulativo. Sin cambios productivos."""
import argparse
import json
from pathlib import Path

from .actualizacion import prevalidar_accidente, guardar_candidato


def main(argv=None):
    p = argparse.ArgumentParser(description="Validación previa sin reentrenar ni publicar.")
    p.add_argument("--origen", required=True, help="Archivo ACCIDENTE.csv acumulativo.")
    p.add_argument("--referencia", default="entregas/entrega_final/dataset_modelado_2017_2025.csv")
    p.add_argument("--corte", required=True, help="Último mes cerrado, formato AAAA-MM.")
    p.add_argument("--salida", default="staging/dataset_modelado_candidato.csv")
    p.add_argument("--reporte", default="staging/reporte_actualizacion.json")
    args = p.parse_args(argv)
    if Path(args.salida).resolve() == Path(args.referencia).resolve():
        p.error("La salida no puede ser el dataset vigente.")
    if Path(args.salida).resolve() == Path(args.origen).resolve():
        p.error("La salida no puede ser ACCIDENTE.csv.")
    candidato, reporte = prevalidar_accidente(
        args.origen, args.referencia, args.corte
    )
    print(json.dumps(reporte, indent=2, ensure_ascii=False))
    # Nunca se publica un candidato con discrepancias históricas o calidad pendiente.
    if reporte["estado"] != "candidato_validado_pendiente_aprobacion":
        print("La comparación no autoriza preparar un archivo candidato.")
        return 2
    salida, auditoria = guardar_candidato(candidato, reporte, args.salida, args.reporte)
    print("Candidato preparado:", salida)
    print("Informe de auditoría:", auditoria)
    print("SIN cambios sobre el histórico vigente, DVC, MLflow o FastAPI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
