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
