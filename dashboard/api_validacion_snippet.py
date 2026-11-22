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
