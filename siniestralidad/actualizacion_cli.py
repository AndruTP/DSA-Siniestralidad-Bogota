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
    # Bloqueo conservador: sin CSV candidato, pero con informe de auditoría.
    if reporte["estado"] != "candidato_validado_pendiente_aprobacion":
        auditoria = Path(args.reporte)
        if auditoria.exists():
            raise FileExistsError(f"El informe ya existe: {auditoria}; usa otra ruta.")
        auditoria.parent.mkdir(parents=True, exist_ok=True)
        auditoria.write_text(
            json.dumps(reporte, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print("Actualización bloqueada; informe guardado en:", auditoria)
        print("NO se creó el dataset candidato. DVC/MLflow/API intactos.")
        return 2
    salida, auditoria = guardar_candidato(candidato, reporte, args.salida, args.reporte)
    print("Candidato preparado:", salida)
    print("Informe de auditoría:", auditoria)
    print("SIN cambios sobre el histórico vigente, DVC, MLflow o FastAPI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
