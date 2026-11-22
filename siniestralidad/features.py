"""Carga, control temporal y variables de V2; sin usar el objetivo del mes pronosticado."""
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNAS_BASE = (
    "LOCALIDAD", "PERIODO", "SINIESTROS", "MES", "ANIO", "MES_SIN",
    "MES_COS", "LAG_1", "LAG_3", "LAG_6", "LAG_12",
    "MEDIA_MOVIL_3", "MEDIA_MOVIL_6", "MEDIA_MOVIL_12",
    "PERIODO_2020_2021",
)


def _validar_panel(df):
    if df.empty:
        raise ValueError("El panel está vacío.")
    if df["LOCALIDAD"].isna().any() or df["LOCALIDAD"].astype(str).str.strip().eq("").any():
        raise ValueError("Hay localidades vacías.")
    if df["PERIODO"].isna().any():
        raise ValueError("PERIODO contiene fechas inválidas.")
    if df.duplicated(["LOCALIDAD", "PERIODO"]).any():
        raise ValueError("Hay registros duplicados de localidad–mes.")
    if not df["PERIODO"].dt.day.eq(1).all():
        raise ValueError("PERIODO debe ser el primer día de cada mes.")
    meses = pd.date_range(df["PERIODO"].min(), df["PERIODO"].max(), freq="MS")
    locales = df["LOCALIDAD"].unique()
    if len(df) != len(meses) * len(locales):
        raise ValueError("Faltan meses o localidades dentro del panel.")
    if not df["ANIO"].eq(df["PERIODO"].dt.year).all():
        raise ValueError("ANIO es inconsistente con PERIODO.")
    if not df["MES"].eq(df["PERIODO"].dt.month).all():
        raise ValueError("MES es inconsistente con PERIODO.")
    if df["SINIESTROS"].isna().any() or (df["SINIESTROS"] < 0).any():
        raise ValueError("SINIESTROS debe contener conteos no negativos.")
    if df[list(COLUMNAS_BASE[3:])].isna().any().any():
        raise ValueError("Hay valores faltantes en las variables del panel.")
    return df


def cargar_dataset_modelado(ruta):
    """Lee el CSV de modelamiento generado en el proyecto.

    La extracción de ACCIDENTE.csv y su versionado DVC son otra etapa: este
    módulo NO sustituye la preparación/depuración del archivo crudo.
    """
    df = pd.read_csv(Path(ruta), encoding="utf-8-sig", low_memory=False)
    faltantes = sorted(set(COLUMNAS_BASE) - set(df.columns))
    if faltantes:
        raise ValueError(f"Faltan columnas: {faltantes}")
    df["PERIODO"] = pd.to_datetime(df["PERIODO"], errors="coerce")
    df["LOCALIDAD"] = df["LOCALIDAD"].astype("string").str.strip().str.upper()
    df = df.sort_values(["LOCALIDAD", "PERIODO"]).reset_index(drop=True)
    return _validar_panel(df)


def agregar_caracteristicas_v2(df):
    """Extrae la celda 42 del notebook, preservando los rezagos históricos.

    ESTACIONAL_CIUDAD usa únicamente el MISMO MES de años anteriores:
    el desplazamiento (shift) es esencial para evitar fuga de información.
    """
    extendido = df.sort_values(["LOCALIDAD", "PERIODO"]).copy()
    serie = extendido.groupby("LOCALIDAD")["SINIESTROS"]

    extendido["EWM_6"] = serie.transform(
        lambda s: s.shift(1).ewm(span=6).mean()
    ).fillna(extendido["MEDIA_MOVIL_12"])

    extendido["RELATIVO"] = (
        extendido["SINIESTROS"]
        / extendido["MEDIA_MOVIL_12"].clip(lower=1)
    )
    ciudad = (
        extendido.groupby(["PERIODO", "MES"], as_index=False)["RELATIVO"]
        .mean().sort_values("PERIODO")
    )
    ciudad["ESTACIONAL_CIUDAD"] = ciudad.groupby("MES")["RELATIVO"].transform(
        lambda s: s.shift(1).expanding().mean()
    )
    extendido = extendido.merge(
        ciudad[["PERIODO", "ESTACIONAL_CIUDAD"]],
        on="PERIODO", how="left",
    )
    extendido["ESTACIONAL_CIUDAD"] = extendido["ESTACIONAL_CIUDAD"].fillna(1.0)
    extendido = extendido.drop(columns="RELATIVO")
    if not np.isfinite(extendido[["EWM_6", "ESTACIONAL_CIUDAD"]].to_numpy(dtype=float)).all():
        raise ValueError("Variables extendidas no finitas.")
    if (extendido["ESTACIONAL_CIUDAD"] <= 0).any():
        raise ValueError("ESTACIONAL_CIUDAD debe ser positiva.")
    return extendido


def construir_siguiente_mes(panel, periodo=None):
    """Crea la matriz del MES SIGUIENTE usando exclusivamente valores observados.

    No admite saltarse meses ni extrapolar a varios meses sin datos intermedios.
    Preserva las medias históricas originales, calculadas con datos anteriores
    a 2017, para mantener consistencia con el notebook V2.
    """
    historico = _validar_panel(panel.copy())
    ultimo = historico["PERIODO"].max()
    siguiente = ultimo + pd.offsets.MonthBegin(1)
    if periodo is not None and pd.Timestamp(periodo) != siguiente:
        raise ValueError(f"Solo se permite el mes inmediatamente siguiente: {siguiente:%Y-%m}.")
    localidades = sorted(historico["LOCALIDAD"].unique())
    if historico["PERIODO"].nunique() < 12:
        raise ValueError("Se requieren al menos 12 meses observados.")

    futuros = []
    for localidad in localidades:
        s = historico.loc[
            historico["LOCALIDAD"].eq(localidad)
        ].sort_values("PERIODO")["SINIESTROS"].astype(float)
        fila = {
            "LOCALIDAD": localidad,
            "PERIODO": siguiente,
            "SINIESTROS": np.nan,
            "MES": siguiente.month,
            "ANIO": siguiente.year,
            "MES_SIN": np.sin(2 * np.pi * siguiente.month / 12),
            "MES_COS": np.cos(2 * np.pi * siguiente.month / 12),
            "PERIODO_2020_2021": int(2020 <= siguiente.year <= 2021),
        }
        for lag in (1, 3, 6, 12):
            fila[f"LAG_{lag}"] = float(s.iloc[-lag])
        for ventana in (3, 6, 12):
            fila[f"MEDIA_MOVIL_{ventana}"] = float(s.iloc[-ventana:].mean())
        futuros.append(fila)

    todo = pd.concat([historico, pd.DataFrame(futuros)], ignore_index=True)
    completo = agregar_caracteristicas_v2(todo)
    pronostico = completo.loc[
        completo["PERIODO"].eq(siguiente)
    ].sort_values("LOCALIDAD").reset_index(drop=True)
    predictores = [c for c in COLUMNAS_BASE if c != "SINIESTROS"] + ["EWM_6", "ESTACIONAL_CIUDAD"]
    if pronostico[predictores].isna().any().any():
        raise ValueError("No se pudieron construir todas las variables del mes futuro.")
    return pronostico
