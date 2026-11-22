# Extracción del pipeline V2 de siniestralidad vial

## Procedencia

La clase `ModeloOffset` procede de la celda 45 y las características
`EWM_6` y `ESTACIONAL_CIUDAD` de la celda 42 del notebook
`entregas/entrega_final/ENTRENAMIENTO_MODELOS_ANALISIS_TERRITORIAL_2024_V2.ipynb`.
La parametrización «Menor complejidad» procede de la celda 68.

**Alcance de esta fase:** consumir el CSV **ya modelado** y extraer el entrenamiento
de manera reutilizable. Aún NO se acepta un nuevo `ACCIDENTE.csv` en la API.
La normalización del archivo crudo, DVC/S3 y los permisos de carga deberán
integrarse y probarse en la siguiente fase.

## Instalar (entorno de EC2 existente)

```bash
cd ~/DSA-Siniestralidad-Bogota
source ~/.venv/bin/activate
python -m unittest discover -s tests -p 'test_pipeline_v2.py' -v
```

## Reproducir candidato V2 sin cambiar el modelo publicado

```bash
python -m siniestralidad.cli entrenar \
  --datos entregas/entrega_final/dataset_modelado_2017_2025.csv
```

Esta ejecución utiliza entrenamiento 2017–2023, validación 2024 y deja
2025 **reservado**. El resultado es un informe local en JSON.
Para registrar una corrida **como candidata, sin promoción**:

```bash
python -m siniestralidad.cli entrenar \
  --datos entregas/entrega_final/dataset_modelado_2017_2025.csv \
  --registrar --tracking-uri http://127.0.0.1:8050
```

No se llama a `register_model`, ni se crean/modifican aliases de producción.

## Pronóstico de un mes adelante con el modelo aprobado

```bash
python -m siniestralidad.cli pronosticar \
  --datos entregas/entrega_final/dataset_modelado_2017_2025.csv \
  --modelo models:/DSA-Siniestralidad-Bogota-Offset/2 \
  --tracking-uri http://127.0.0.1:8050
```

El resultado se guarda en `resultados_pipeline/proyeccion_siguiente_mes.csv`.
Con los datos actuales hasta diciembre de 2025, el siguiente mes válido
es **enero de 2026**. No extrapola hasta diciembre de 2026 sin observaciones
intermedias. Es una proyección de un paso adelante, no una validación de 2024.

## Controles y límites importantes

- No reentrena al consultar pronósticos. El subcomando `pronosticar` carga
  explícitamente una URI de modelo aprobada.
- No reemplaza automáticamente MLflow V2. Cualquier nuevo modelo es candidato.
- La evaluación de 2025 **no se ejecuta en esta fase**.
- El CSV de modelamiento ya incluye rezagos de 2016 para los primeros meses
  de 2017. Esos rezagos se conservan, no se inventan.
- No se debe afirmar que V2 supera la línea base: en el notebook V2
  la ganancia de validación observada es inferior al umbral objetivo del 10 %.
- La nueva interfaz de carga y promoción requiere autenticación y validación
  independiente antes de exponer acciones administrativas a Internet.
- Para reconstruir fielmente el entrenamiento hay que conservar versiones de
  Python, pandas, scikit-learn y la huella SHA-256 del dataset.
