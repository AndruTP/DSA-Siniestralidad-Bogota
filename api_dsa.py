from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
import mlflow
import pandas as pd

app = FastAPI(title="DSA - Siniestralidad Bogotá")

mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:8050"))

MODEL_URI = os.environ.get("MODEL_URI", "models:/DSA-Siniestralidad-Bogota-Offset/2")
# Docker puede usar una copia aprobada y verificada del mismo modelo V2.
# Sin MODEL_LOAD_URI se conserva el comportamiento original de EC2.
modelo = mlflow.pyfunc.load_model(os.environ.get("MODEL_LOAD_URI", MODEL_URI))

ruta_datos = Path(
    "entregas/entrega_final/dataset_modelado_2017_2025.csv"
)

df = pd.read_csv(ruta_datos, parse_dates=["PERIODO"])
df = df.sort_values(["LOCALIDAD", "PERIODO"]).copy()

serie = df.groupby("LOCALIDAD")["SINIESTROS"]

df["EWM_6"] = serie.transform(
    lambda s: s.shift(1).ewm(span=6).mean()
).fillna(df["MEDIA_MOVIL_12"])

df["RELATIVO"] = (
    df["SINIESTROS"] /
    df["MEDIA_MOVIL_12"].clip(lower=1)
)

ciudad = (
    df.groupby(["PERIODO", "MES"], as_index=False)["RELATIVO"]
    .mean()
    .sort_values("PERIODO")
)

ciudad["ESTACIONAL_CIUDAD"] = (
    ciudad.groupby("MES")["RELATIVO"]
    .transform(lambda s: s.shift(1).expanding().mean())
)

df = df.merge(
    ciudad[["PERIODO", "ESTACIONAL_CIUDAD"]],
    on="PERIODO",
    how="left"
)

df["ESTACIONAL_CIUDAD"] = df["ESTACIONAL_CIUDAD"].fillna(1.0)

columnas = modelo.metadata.get_input_schema().input_names()

@app.get("/health")
def health():
    return {"status": "ok", "modelo": MODEL_URI}

@app.get("/api/localidades")
def localidades():
    return sorted(df["LOCALIDAD"].unique().tolist())

@app.get("/api/predict")
def predict(localidad: str, periodo: str):
    try:
        fecha = pd.to_datetime(periodo, format="%Y-%m")
    except ValueError:
        raise HTTPException(400, "Periodo inválido. Use AAAA-MM")

    # Demostración retrospectiva: validación 2024
    if fecha.year != 2024:
        raise HTTPException(
            400, "Esta versión solo permite consultar la validación 2024"
        )

    fila = df[
        (df["LOCALIDAD"] == localidad.upper()) &
        (df["PERIODO"] == fecha)
    ]

    if fila.empty:
        raise HTTPException(404, "Localidad o periodo no encontrado")

    pred = modelo.predict(fila[columnas])

    return {
        "localidad": localidad.upper(),
        "periodo": periodo,
        "prediccion": round(float(pred[0]), 2),
        "observado": int(fila["SINIESTROS"].iloc[0]),
        "tipo": "Validación histórica 2024",
        "modelo": MODEL_URI
    }

@app.get("/")
def dashboard():
    return FileResponse("tablero_siniestralidad.html")

app.mount(
    "/dashboard",
    StaticFiles(directory="dashboard"),
    name="dashboard"
)
# DSA-06 · Endpoint de validación retrospectiva en lote.
# Anexar al final de api_dsa.py después de la definición de 'modelo', 'df', 'columnas'.
# Recupera las predicciones del modelo MLflow V2 cargado por la API.
@app.get("/api/validacion")
def validacion_2024():
    validacion = df[df["PERIODO"].dt.year.eq(2024)].copy()
    validacion = validacion.sort_values(["PERIODO", "LOCALIDAD"])
    if len(validacion) != 228:
        raise HTTPException(500, f"Validación incompleta: {len(validacion)} filas")
    estimaciones = modelo.predict(validacion[columnas])
    return {
        "modelo": MODEL_URI,
        "periodo_validacion": "2024",
        "filas": [
            {
                "localidad": str(fila.LOCALIDAD),
                "periodo": fila.PERIODO.strftime("%Y-%m"),
                "prediccion": round(float(pred), 6),
                "observado": int(fila.SINIESTROS),
                "base_mm12": round(float(fila.MEDIA_MOVIL_12), 6),
                "mismo_mes_anterior": int(fila.LAG_12),
            }
            for fila, pred in zip(validacion.itertuples(index=False), estimaciones)
        ],
    }
# Fragmento para anexar UNA SOLA VEZ al final de api_dsa.py.
# Reutiliza los objetos existentes: app, df, modelo, columnas y MODEL_URI.
# No entrena, no registra y no promueve modelos en MLflow.
# El periodo solicitado debe ser exactamente el siguiente al ultimo observado.
@app.get("/api/pronostico")
def api_pronostico(periodo: str | None = None):
    import numpy as np
    from fastapi import HTTPException
    from siniestralidad.features import construir_siguiente_mes

    try:
        siguiente = construir_siguiente_mes(df, periodo=periodo)
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    predicciones = np.asarray(modelo.predict(siguiente[columnas]), dtype=float)
    if len(predicciones) != len(siguiente) or not np.isfinite(predicciones).all() or (predicciones < 0).any():
        raise HTTPException(status_code=500, detail="Modelo produjo predicciones invalidas")

    filas = [
        {
            "localidad": str(f.LOCALIDAD),
            "periodo": f.PERIODO.strftime("%Y-%m"),
            "prediccion": round(float(p), 6),
            "media_movil_12": round(float(f.MEDIA_MOVIL_12), 6),
            "mismo_mes_anterior": round(float(f.LAG_12), 6),
        }
        for f, p in zip(siguiente.itertuples(index=False), predicciones)
    ]
    filas.sort(key=lambda f: f["prediccion"], reverse=True)
    for puesto, fila in enumerate(filas, start=1):
        fila["prioridad_volumen"] = puesto

    return {
        "tipo": "pronostico_fuera_de_muestra",
        "modelo": MODEL_URI,
        "ultimo_mes_observado": df["PERIODO"].max().strftime("%Y-%m"),
        "periodo": siguiente["PERIODO"].iloc[0].strftime("%Y-%m"),
        "numero_localidades": len(filas),
        "predicciones": filas,
        "advertencia": "Orden por volumen esperado, no asignacion optima de recursos.",
    }
# Añadir UNA SOLA VEZ al final de api_dsa.py, después de /api/pronostico.
# Actualización administrativa local: puede utilizarse mediante túnel SSH.
# SIN entrenamiento automático y SIN publicación automática de modelos.
from pathlib import Path as _Path
import hashlib as _hashlib
import json as _json
import os as _os
import shutil as _shutil
import uuid as _uuid

from fastapi import HTTPException as _HTTPException, Request as _Request
from starlette.concurrency import run_in_threadpool as _run_in_threadpool

from siniestralidad.actualizacion import (
    prevalidar_accidente as _prevalidar,
    guardar_candidato as _guardar_candidato,
    _hash_archivo as _hash_archivo_datos,
)
from siniestralidad.features import (
    cargar_dataset_modelado as _cargar_modelado,
    agregar_caracteristicas_v2 as _caracteristicas,
)

_RAIZ = _Path(__file__).resolve().parent
_OPERACION = _RAIZ / "runtime" / "actualizaciones"
_PENDIENTES = _OPERACION / "pendientes"
_ACTIVO = _OPERACION / "activo" / "dataset_modelado.csv"
_META_ACTIVA = _OPERACION / "activo" / "version.json"
_REFERENCIA_ORIGINAL = _RAIZ / "entregas" / "entrega_final" / "dataset_modelado_2017_2025.csv"
_LIMITE_CSV = 450 * 1024 * 1024


def _solo_local(request: _Request):
    # Protege endpoints destructivos en el EC2 público. Para operar desde
    # Windows, conectar con SSH -L y abrir http://127.0.0.1:8002.
    ip = request.client.host if request.client else ""
    if ip not in ("127.0.0.1", "::1"):
        raise _HTTPException(
            status_code=403,
            detail="Administración únicamente vía localhost/túnel SSH. "
                   "No enviar datos ni claves administrativas por HTTP público.",
        )


def _panel_activo():
    return _ACTIVO if _ACTIVO.is_file() else _REFERENCIA_ORIGINAL


def _cargar_panel_activo():
    global df
    # Reconstruye las dos variables de V2 sin alterar el modelo servido.
    df = _caracteristicas(_cargar_modelado(_panel_activo()))


# Recuperar la última versión aprobada al reiniciar Uvicorn.
if _ACTIVO.exists():
    _cargar_panel_activo()


@app.get("/api/historico")
def historico_actualizado():
    return {
        "fecha_corte": df["PERIODO"].max().strftime("%Y-%m"),
        "historico": [
            {
                "LOCALIDAD": str(f.LOCALIDAD),
                "PERIODO": f.PERIODO.strftime("%Y-%m-%d"),
                "SINIESTROS": int(f.SINIESTROS),
            }
            for f in df[["LOCALIDAD", "PERIODO", "SINIESTROS"]]
                .itertuples(index=False)
        ],
    }


@app.get("/api/estado-datos")
def estado_datos():
    return {
        "corte": df["PERIODO"].max().strftime("%Y-%m"),
        "localidades": int(df["LOCALIDAD"].nunique()),
        "filas": int(len(df)),
        "dataset_actualizado": bool(_ACTIVO.exists()),
        "modelo_servido": MODEL_URI,
        "actualizacion": "carga y aprobación explícitas; consulta sin reentrenamiento",
    }


@app.get("/api/admin/estado")
def admin_estado(request: _Request):
    _solo_local(request)
    version = _json.loads(_META_ACTIVA.read_text(encoding="utf-8")) if _META_ACTIVA.exists() else {}
    return {"ultimo_mes_observado": df["PERIODO"].max().strftime("%Y-%m"),
            "modelo": MODEL_URI, "version_datos": version,
            "origen_de_datos": "runtime/actualizaciones/activo" if _ACTIVO.exists()
                                else "dataset original de la entrega"}


@app.post("/api/admin/preparar")
async def admin_preparar(request: _Request, corte: str):
    _solo_local(request)
    # HTTP octet-stream; no dependencia de python-multipart. Se escribe
    # en chunks para no cargar ~237 MB completos en memoria.
    _PENDIENTES.mkdir(parents=True, exist_ok=True)
    operacion_id = _uuid.uuid4().hex
    carpeta = _PENDIENTES / operacion_id
    carpeta.mkdir(parents=True, exist_ok=False)
    bruto = carpeta / "ACCIDENTE.csv"
    total = 0
    try:
        with bruto.open("wb") as destino:
            async for bloque in request.stream():
                total += len(bloque)
                if total > _LIMITE_CSV:
                    raise _HTTPException(
                        status_code=413, detail="El CSV supera el límite de 450 MB."
                    )
                destino.write(bloque)
        if total == 0:
            raise _HTTPException(400, "Se recibió un CSV vacío.")
        referencia = _panel_activo()
        candidato, reporte = await _run_in_threadpool(
            _prevalidar, bruto, referencia, corte,
        )
        # Permitir revisión de diferencias históricas. El usuario debe
        # APROBAR explícitamente, nunca se sobrescribe aquí.
        salida = carpeta / "dataset_candidato.csv"
        auditoria = carpeta / "auditoria.json"
        await _run_in_threadpool(
            _guardar_candidato, candidato, reporte, salida, auditoria,
        )
        return {
            "id": operacion_id,
            "estado": "pendiente_aprobacion",
            "corte": reporte["fecha_corte"],
            "meses_nuevos": reporte["meses_nuevos"],
            "cambios_historicos": reporte["historial_modificado_filas"],
            "fechas_invalidas": reporte["fechas_invalidas_victimas"],
            "localidades_desconocidas": reporte["localidades_desconocidas"],
            "filas_candidatas": reporte["filas_candidatas"],
            "observacion": (
                "Se preparó el candidato. Las diferencias históricas requieren "
                "revisión antes de pulsar Activar; aún no se modificó la aplicación."
            ),
        }
    except _HTTPException:
        _shutil.rmtree(carpeta, ignore_errors=True)
        raise
    except Exception as exc:
        _shutil.rmtree(carpeta, ignore_errors=True)
        raise _HTTPException(422, f"Archivo rechazado: {exc}") from exc


@app.post("/api/admin/activar/{operacion_id}")
async def admin_activar(request: _Request, operacion_id: str):
    _solo_local(request)
    if len(operacion_id) != 32 or any(c not in "0123456789abcdef" for c in operacion_id):
        raise _HTTPException(400, "Identificador inválido.")
    carpeta = _PENDIENTES / operacion_id
    auditoria = carpeta / "auditoria.json"
    candidato = carpeta / "dataset_candidato.csv"
    if not auditoria.exists() or not candidato.exists():
        raise _HTTPException(404, "No existe el candidato solicitado.")
    reporte = _json.loads(auditoria.read_text(encoding="utf-8"))
    if reporte.get("aprobado", False):
        raise _HTTPException(409, "El candidato ya fue utilizado.")
    if _hash_archivo_datos(candidato) != reporte["hash_sha256_candidato"]:
        raise _HTTPException(409, "El dataset cambió desde su prevalidación.")

    # Validar estructura y preparar memoria antes de sustituir el activo.
    try:
        nuevo_panel = await _run_in_threadpool(
            lambda: _caracteristicas(_cargar_modelado(candidato))
        )
    except Exception as exc:
        raise _HTTPException(422, f"Dataset candidato no válido: {exc}") from exc

    _ACTIVO.parent.mkdir(parents=True, exist_ok=True)
    temporal = _ACTIVO.with_name("dataset_modelado.tmp")
    copia_anterior = _ACTIVO.with_name("dataset_modelado_anterior.csv")
    if _ACTIVO.exists():
        _shutil.copy2(_ACTIVO, copia_anterior)
    _shutil.copy2(candidato, temporal)
    _os.replace(temporal, _ACTIVO)
    global df
    df = nuevo_panel

    version = {
        "id": operacion_id,
        "fecha_corte": reporte["fecha_corte"],
        "cambios_historicos_aceptados": reporte["historial_modificado_filas"],
        "localidades_desconocidas": reporte["localidades_desconocidas"],
        "sha256": reporte["hash_sha256_candidato"],
        "modelo_se_mantuvo": MODEL_URI,
        "modelo_reentrenado": False,
        "origen": "ACCIDENTE.csv cargado por administrador",
    }
    tmpmeta = _META_ACTIVA.with_suffix(".tmp")
    tmpmeta.write_text(_json.dumps(version, ensure_ascii=False, indent=2), encoding="utf-8")
    _os.replace(tmpmeta, _META_ACTIVA)
    reporte["aprobado"] = True
    auditoria.write_text(_json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "estado": "datos_activados",
        "fecha_corte": version["fecha_corte"],
        "siguiente_mes": (df["PERIODO"].max() + __import__("pandas").offsets.MonthBegin(1)).strftime("%Y-%m"),
        "localidades": int(df["LOCALIDAD"].nunique()),
        "modelo": MODEL_URI,
        "reentrenado": False,
        "indicacion": "Actualiza el Dashboard: histórico y /api/pronostico usan este dataset.",
    }
