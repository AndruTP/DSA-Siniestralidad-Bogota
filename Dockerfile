# Una única imagen Python para la API y para el perfil MLflow de Compose.
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements-docker.txt /app/requirements-docker.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements-docker.txt

RUN useradd --uid 1000 --home-dir /home/ubuntu --create-home --shell /bin/sh appuser
COPY --chown=appuser:appuser api_dsa.py tablero_siniestralidad.html /app/
COPY --chown=appuser:appuser siniestralidad/ /app/siniestralidad/
COPY --chown=appuser:appuser dashboard/ /app/dashboard/
COPY --chown=appuser:appuser entregas/entrega_final/dataset_modelado_2017_2025.csv /app/entregas/entrega_final/dataset_modelado_2017_2025.csv

USER appuser
EXPOSE 18001
CMD ["sh", "-c", "if [ -n \"$RAILWAY_PROJECT_ID\" ]; then exec uvicorn api_dsa:app --host 0.0.0.0 --port \"${PORT:?Railway debe asignar PORT}\"; fi; exec uvicorn api_dsa:app --host 127.0.0.1 --port 18001"]
