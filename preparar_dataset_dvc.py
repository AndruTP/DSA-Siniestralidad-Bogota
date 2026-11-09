from IPython.display import display

import pandas as pd
import numpy as np
from pathlib import Path
df_eda = pd.read_csv("ACCIDENTE.csv", encoding="utf-8-sig", low_memory=False)
# ==================================================
# 03. AUDITORÍA AVANZADA DE CALIDAD DE DATOS
# ==================================================

import pandas as pd
import numpy as np

# Trabajamos sobre una copia
eda = df_eda.copy()

# Normalizar únicamente columnas críticas
columnas_categoricas = [
    "LOCALIDAD", "GRAVEDAD", "CLASE_ACC",
    "BARRIO", "MVINOMBRE"
]

for col in columnas_categoricas:
    eda[col] = (
        eda[col].astype("string")
        .str.strip().str.upper()
    )

# Interpretar fechas; conservamos la fecha original
eda["FECHA_ANALISIS"] = pd.to_datetime(
    eda["FECHA_OCURRENCIA_ACC"],
    errors="coerce",
    utc=True
).dt.tz_localize(None)




# ========================================================
# 08. MATRIZ TEMPORAL Y TERRITORIAL
# Siniestros registrados con heridos o muertos
# ========================================================

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

victimas = eda.loc[
    eda["GRAVEDAD"].isin(["CON HERIDOS", "CON MUERTOS"])
    & eda["FECHA_ANALISIS"].dt.year.between(2016, 2025)
].copy()

victimas["PERIODO"] = (
    victimas["FECHA_ANALISIS"]
    .dt.to_period("M")
    .dt.to_timestamp()
)

# Contar siniestros, NO número de personas lesionadas
mensual_localidad = (
    victimas
    .groupby(["LOCALIDAD", "PERIODO"])
    .size()
    .rename("SINIESTROS")
    .reset_index()
)

# Panel mensual completo para análisis exploratorio
localidades = sorted(eda["LOCALIDAD"].dropna().unique())
meses = pd.date_range(
    "2016-01-01", "2025-12-01", freq="MS"
)

indice = pd.MultiIndex.from_product(
    [localidades, meses],
    names=["LOCALIDAD", "PERIODO"]
)

panel = (
    mensual_localidad
    .set_index(["LOCALIDAD", "PERIODO"])
    .reindex(indice, fill_value=0)
    .reset_index()
)




# ========================================================
# 10. ESTACIONALIDAD Y PATRONES TERRITORIALES
# Siniestros con heridos o muertos, 2016–2025
# ========================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

panel_modelo = panel.loc[
    panel["LOCALIDAD"] != "SUMAPAZ"
].copy()

panel_modelo["ANIO"] = panel_modelo["PERIODO"].dt.year
panel_modelo["MES"] = panel_modelo["PERIODO"].dt.month



# ==========================================================
# 12. PREPARACIÓN DEL DATASET PARA MODELAMIENTO
# Predicción: siniestros del mes por localidad
# ==========================================================

import numpy as np
import pandas as pd

modelo_df = (
    panel_modelo[
        ["LOCALIDAD", "PERIODO", "SINIESTROS"]
    ]
    .copy()
    .sort_values(["LOCALIDAD", "PERIODO"])
    .reset_index(drop=True)
)

# Características calendario
modelo_df["MES"] = modelo_df["PERIODO"].dt.month
modelo_df["ANIO"] = modelo_df["PERIODO"].dt.year

# Codificación cíclica del mes
modelo_df["MES_SIN"] = np.sin(
    2 * np.pi * modelo_df["MES"] / 12
)
modelo_df["MES_COS"] = np.cos(
    2 * np.pi * modelo_df["MES"] / 12
)

# Agrupar por localidad para evitar mezclar territorios
grupo = modelo_df.groupby("LOCALIDAD")["SINIESTROS"]

# Rezagos: solo información histórica
for rezago in [1, 3, 6, 12]:
    modelo_df[f"LAG_{rezago}"] = grupo.shift(rezago)

# Medias móviles desplazadas un mes
for ventana in [3, 6, 12]:
    modelo_df[f"MEDIA_MOVIL_{ventana}"] = (
        modelo_df
        .groupby("LOCALIDAD")["SINIESTROS"]
        .transform(
            lambda s: s.shift(1).rolling(
                ventana, min_periods=ventana
            ).mean()
        )
    )

# Indicador histórico de contexto
modelo_df["PERIODO_2020_2021"] = (
    modelo_df["ANIO"].between(2020, 2021)
).astype(int)

# Eliminar solo las filas sin historial suficiente
modelo_ml = modelo_df.dropna(
    subset=[
        "LAG_12",
        "MEDIA_MOVIL_12"
    ]
).copy()

print("Registros del panel original:", len(modelo_df))
print("Registros listos para ML:", len(modelo_ml))
print("Número de localidades:",
      modelo_ml["LOCALIDAD"].nunique())

print("\nIntervalo temporal:")
print(
    modelo_ml["PERIODO"].min(),
    "a",
    modelo_ml["PERIODO"].max()
)

print("\nPrimeras observaciones:")
display(modelo_ml.head(10))

print("\nValores nulos:")
display(modelo_ml.isna().sum().to_frame("Nulos"))


# ========================================================
# 13. VALIDACIÓN FINAL DEL DATASET PREPARADO
# ========================================================

assert len(modelo_ml) == 2052, \
    "Cantidad inesperada de observaciones"

assert modelo_ml["LOCALIDAD"].nunique() == 19, \
    "Cantidad inesperada de localidades"

assert not modelo_ml.duplicated(
    ["LOCALIDAD", "PERIODO"]
).any(), "Existen periodos duplicados"

assert modelo_ml.isna().sum().sum() == 0, \
    "Existen valores nulos"

# Comprobar la lógica del rezago de un mes
comprobacion = modelo_df.copy()

comprobacion["LAG_1_VERIFICADO"] = (
    comprobacion.groupby("LOCALIDAD")["SINIESTROS"]
    .shift(1)
)

assert (
    comprobacion["LAG_1"]
    .fillna(-1)
    .eq(comprobacion["LAG_1_VERIFICADO"].fillna(-1))
    .all()
), "Error en el cálculo de LAG_1"



modelo_ml.to_csv("dataset_modelado_2017_2025.csv", index=False, encoding="utf-8-sig")
print("DATASET GENERADO:", len(modelo_ml), "registros;",
      modelo_ml["LOCALIDAD"].nunique(), "localidades")
