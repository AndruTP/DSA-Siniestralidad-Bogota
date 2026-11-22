"""Prevalidación de actualizaciones acumulativas de ACCIDENTE.csv.

No altera el dataset vigente, el DVC remoto, MLflow ni FastAPI.
Usa chunks para procesar el CSV original (~237 MB) sin cargarlo entero.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .features import cargar_dataset_modelado, COLUMNAS_BASE

CAMPOS_ORIGEN = ["LOCALIDAD", "GRAVEDAD", "FECHA_OCURRENCIA_ACC"]
VICTIMAS = {"CON HERIDOS", "CON MUERTOS"}


def _hash_archivo(ruta):
    digest = hashlib.sha256()
    with Path(ruta).open("rb") as fh:
        for bloque in iter(lambda: fh.read(4 * 1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _mes(valor):
    fecha = pd.to_datetime(valor, errors="raise")
    if pd.isna(fecha) or fecha.day != 1:
        raise ValueError("El corte debe ser AAAA-MM, primer día del mes.")
    return pd.Timestamp(fecha).to_period("M").to_timestamp()


def _ultimo_mes_cerrado():
    hoy = pd.Timestamp(datetime.now(ZoneInfo("America/Bogota")).date())
    return hoy.to_period("M").to_timestamp() - pd.offsets.MonthBegin(1)


def _armar_dataset(contador, localidades, corte):
    meses = pd.date_range("2016-01-01", corte, freq="MS")
    indice = pd.MultiIndex.from_product(
        [sorted(localidades), meses], names=["LOCALIDAD", "PERIODO"]
    )
    serie = pd.Series(contador, dtype="int64", name="SINIESTROS")
    if len(serie):
        serie.index = pd.MultiIndex.from_tuples(
            serie.index, names=["LOCALIDAD", "PERIODO"]
        )
    else:
        serie.index = pd.MultiIndex.from_arrays(
            [[], []], names=["LOCALIDAD", "PERIODO"]
        )
    panel = serie.reindex(indice, fill_value=0).reset_index()
    panel = panel.sort_values(["LOCALIDAD", "PERIODO"]).reset_index(drop=True)
    panel["MES"] = panel["PERIODO"].dt.month
    panel["ANIO"] = panel["PERIODO"].dt.year
    panel["MES_SIN"] = np.sin(2 * np.pi * panel["MES"] / 12)
    panel["MES_COS"] = np.cos(2 * np.pi * panel["MES"] / 12)
    grupos = panel.groupby("LOCALIDAD")["SINIESTROS"]
    for rezago in (1, 3, 6, 12):
        panel[f"LAG_{rezago}"] = grupos.shift(rezago)
    for ventana in (3, 6, 12):
        panel[f"MEDIA_MOVIL_{ventana}"] = grupos.transform(
            lambda s: s.shift(1).rolling(ventana, min_periods=ventana).mean()
        )
    panel["PERIODO_2020_2021"] = panel["ANIO"].between(2020, 2021).astype(int)
    panel = panel.loc[panel["PERIODO"] >= "2017-01-01", list(COLUMNAS_BASE)]
    if panel.isna().any().any() or panel.duplicated(["LOCALIDAD", "PERIODO"]).any():
        raise ValueError("El dataset resultante contiene nulos o localidad-mes repetidos.")
    return panel


def prevalidar_accidente(origen, referencia, corte, *, chunksize=60000):
    """Compara una nueva base acumulativa con todos los conteos vigentes.

    Requiere TODOS los registros históricos 2016–corte. Nunca interpreta
    filas ausentes de un mes como cero sin marcar la limitación en el reporte.
    """
    origen, referencia = Path(origen), Path(referencia)
    if not origen.is_file():
        raise FileNotFoundError(origen)
    corte = _mes(corte)
    if corte > _ultimo_mes_cerrado():
        raise ValueError(
            f"El mes {corte:%Y-%m} todavía no está cerrado. "
            "No se permite proyectar a partir de datos de un mes en curso."
        )
    ref = cargar_dataset_modelado(referencia)
    ultimo_vigente = ref["PERIODO"].max()
    if corte < ultimo_vigente:
        raise ValueError(
            f"El corte {corte:%Y-%m} es anterior al histórico vigente "
            f"({ultimo_vigente:%Y-%m})."
        )
    localidades = sorted(ref["LOCALIDAD"].unique().tolist())
    if len(localidades) != 19:
        raise ValueError("La referencia no contiene las 19 localidades esperadas.")

    # La memoria depende del tamaño del chunk y de meses×localidades.
    conteos = Counter()
    total_filas = victimas_total = invalidas_fecha = desconocidas = 0
    max_fecha = None
    min_fecha = None
    meses_fuera = 0
    categorias_desconocidas = Counter()

    for parte in pd.read_csv(
        origen, encoding="utf-8-sig", usecols=CAMPOS_ORIGEN,
        dtype="string", chunksize=chunksize, low_memory=False,
    ):
        total_filas += len(parte)
        parte["LOCALIDAD"] = parte["LOCALIDAD"].str.strip().str.upper()
        parte["GRAVEDAD"] = parte["GRAVEDAD"].str.strip().str.upper()
        victima = parte["GRAVEDAD"].isin(VICTIMAS)
        victimas_total += int(victima.sum())
        if not victima.any():
            continue
        filas = parte.loc[victima].copy()
        # Mantiene la interpretación temporal usada en preparar_dataset_dvc.py.
        fechas = pd.to_datetime(
            filas["FECHA_OCURRENCIA_ACC"], errors="coerce", utc=True
        ).dt.tz_localize(None)
        invalidas_fecha += int(fechas.isna().sum())
        fechas_ok = fechas.dropna()
        if len(fechas_ok):
            max_chunk, min_chunk = fechas_ok.max(), fechas_ok.min()
            max_fecha = max(max_fecha, max_chunk) if max_fecha is not None else max_chunk
            min_fecha = min(min_fecha, min_chunk) if min_fecha is not None else min_chunk
        filas = filas.loc[fechas.notna()].copy()
        if filas.empty:
            continue
        filas["PERIODO"] = fechas.loc[filas.index].dt.to_period("M").dt.to_timestamp()
        rango = filas["PERIODO"].between(pd.Timestamp("2016-01-01"), corte)
        meses_fuera += int((~rango).sum())
        filas = filas.loc[rango]
        locales_validos = filas["LOCALIDAD"].isin(localidades)
        desconocidas += int((~locales_validos).sum())
        categorias_desconocidas.update(
            filas.loc[~locales_validos, "LOCALIDAD"].fillna("VACIA").astype(str)
        )
        filas = filas.loc[locales_validos]
        conteos.update(
            {(str(loc), pd.Timestamp(mes)): int(n)
             for (loc, mes), n in filas.groupby(["LOCALIDAD", "PERIODO"]).size().items()}
        )

    if total_filas == 0 or victimas_total == 0 or not conteos:
        raise ValueError("ACCIDENTE.csv no contiene datos válidos del periodo.")
    candidato = _armar_dataset(conteos, localidades, corte)
    actual = ref.set_index(["LOCALIDAD", "PERIODO"])["SINIESTROS"].astype(int)
    nuevo = candidato.set_index(["LOCALIDAD", "PERIODO"])["SINIESTROS"].astype(int)
    dif = (nuevo.reindex(actual.index) != actual)
    inconsistencias = int(dif.sum())
    # Guardar diagnóstico completo, no solo diez ejemplos, para revisión humana.
    cambios = [
        {"localidad": idx[0], "mes": idx[1].strftime("%Y-%m"),
         "vigente": int(actual.loc[idx]), "candidato": int(nuevo.loc[idx]),
         "diferencia": int(nuevo.loc[idx] - actual.loc[idx])}
        for idx in actual.index[dif]
    ]
    ejemplos = cambios[:10]
    cambios_por_anio = dict(sorted(Counter(
        row["mes"][:4] for row in cambios
    ).items()))
    cambios_por_mes = dict(sorted(Counter(
        row["mes"] for row in cambios
    ).items()))
    periodo_nuevo = candidato[candidato["PERIODO"] > ultimo_vigente]
    agregados_mes = {
        t.strftime("%Y-%m"): int(s)
        for t, s in periodo_nuevo.groupby("PERIODO")["SINIESTROS"].sum().items()
    }
    meses_cero = [m for m, total in agregados_mes.items() if total == 0]
    if meses_cero:
        raise ValueError(
            "Meses nuevos sin siniestros de víctimas en todas las localidades: "
            + ", ".join(meses_cero)
        )
    estado = (
        "bloqueado_historial_inconsistente" if inconsistencias else
        "requiere_revision_calidad" if (invalidas_fecha or desconocidas) else
        "candidato_validado_pendiente_aprobacion"
    )
    reporte = {
        "estado": estado,
        "fuente": str(origen),
        "fecha_corte": corte.strftime("%Y-%m"),
        "ultimo_mes_vigente": ultimo_vigente.strftime("%Y-%m"),
        "primer_mes_nuevo": (
            periodo_nuevo["PERIODO"].min().strftime("%Y-%m")
            if not periodo_nuevo.empty else None
        ),
        "filas_origen": total_filas,
        "filas_con_victimas": victimas_total,
        "fechas_invalidas_victimas": invalidas_fecha,
        "localidades_desconocidas": desconocidas,
        "ejemplos_localidades_desconocidas": dict(categorias_desconocidas.most_common(10)),
        "filas_fuera_intervalo": meses_fuera,
        "primera_fecha_victimas": min_fecha.isoformat() if min_fecha is not None else None,
        "ultima_fecha_victimas": max_fecha.isoformat() if max_fecha is not None else None,
        "hash_sha256_origen": _hash_archivo(origen),
        "hash_sha256_referencia": _hash_archivo(referencia),
        "historial_modificado_filas": inconsistencias,
        "ejemplos_cambios_historicos": ejemplos,
        "cambios_historicos": cambios,
        "cambios_por_anio": cambios_por_anio,
        "cambios_por_mes": cambios_por_mes,
        "variacion_neta_historico": int(sum(x["diferencia"] for x in cambios)),
        "variacion_absoluta_historico": int(sum(abs(x["diferencia"]) for x in cambios)),
        "meses_nuevos": agregados_mes,
        "localidades": len(localidades),
        "filas_candidatas": len(candidato),
        "aprobado": False,
        "dvc_actualizado": False,
        "modelo_reentrenado": False,
        "modelo_promovido": False,
        "nota": (
            "Prevalidación sin escritura sobre datos vigentes. La completitud "
            "del último mes debe confirmarse con la fuente SDM antes de aprobar."
        ),
    }
    return candidato, reporte


def guardar_candidato(candidato, reporte, salida, auditoria):
    """Escribe únicamente archivos de STAGING; nunca sobreescribe."""
    salida, auditoria = Path(salida), Path(auditoria)
    if salida.exists() or auditoria.exists():
        raise FileExistsError(
            "El candidato o el informe ya existe; indique nuevas rutas."
        )
    salida.parent.mkdir(parents=True, exist_ok=True)
    auditoria.parent.mkdir(parents=True, exist_ok=True)
    candidato.to_csv(salida, index=False, encoding="utf-8-sig")
    reporte = dict(reporte)
    reporte["dataset_candidato"] = str(salida)
    reporte["hash_sha256_candidato"] = _hash_archivo(salida)
    auditoria.write_text(
        json.dumps(reporte, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return salida, auditoria
