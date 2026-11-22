# Incidente operativo — EC2 AWS Academy: conectividad, recursos y recuperación
**Fecha:** 2026-11-22 · **Proyecto:** DSA-Siniestralidad-Bogota · **Ambiente:** AWS Academy Learner Lab, Ubuntu EC2 `t2.medium` (2 vCPU, ~4 GiB de RAM).

## Contexto y efecto sobre el trabajo

Durante la implementación de FastAPI + MLflow V2 + Docker Compose se presentaron varias interrupciones o bloqueos de acceso a EC2, con reanudaciones y recuperación manual que ralentizaron el avance. Los síntomas incluyeron:
- EC2 Instance Connect atascado en «Estableciendo conexión…».
- SSH desde Windows fallando con `Connection timed out during banner exchange` hacia puerto 22.
- Consola EC2 mostrando temporalmente `Running` y comprobaciones de estado `2/2` correctas mientras no funcionaba SSH.
- Al reconectar, `uptime` indicó aproximadamente **1 minuto** de actividad, compatible con un reinicio reciente.
- La variabilidad en la disponibilidad de AWS Academy obligó a interrumpir pruebas y reconectar repetidamente.

**Impacto:** tiempo invertido recuperando accesos y servicios, riesgo de pérdida de estado no persistente y bloqueo temporal de la prueba del segundo contenedor. No existe una medición fiable de minutos perdidos: no estimarla como hecho.

## Evidencia capturada en EC2 tras recuperar terminal

| Observación | Valor observado |
|---|---|
| RAM total | 3,8 GiB |
| RAM utilizada con FastAPI + MLflow Docker | 2,6 GiB |
| RAM disponible en ese momento | 1,2 GiB |
| Swap | 0 B (no configurada) |
| MLflow Docker | 1,936 GiB, 50,74 % de RAM; 102 PIDs |
| FastAPI Docker | 308,1 MiB, 7,89 % de RAM; 6 PIDs |
| Carga `uptime` tras reconexión | 1,47 / 0,49 / 0,17; uptime ~1 min |
| Mensajes OOM recientes, kernel del arranque actual | Sin coincidencias en `journalctl -k --since "2 hours ago" | grep -Ei 'out of memory|oom|killed process'` |
| MLflow Docker | Inicialmente `healthy`, después detenido voluntariamente |
| FastAPI Docker | `healthy` |
| RAM tras detener exclusivamente MLflow Docker | 791 MiB usada; **3,0 GiB disponible** |
| Prueba FastAPI sin MLflow Docker | **OK**, corte 2026-10, 2.242 filas, 19 localidades, predicción 2026-11, 228 registros validación 2024, Kennedy 107.815756 |

La API Docker consume el **artefacto local V2 exportado en `runtime/serving/modelo_v2`**, por lo que NO requiere mantener el servidor de seguimiento MLflow levantado para pronosticar.

## Interpretación y límites de la evidencia

- **Hecho comprobado:** levantar MLflow Docker elevó significativamente el consumo de RAM; detenerlo liberó alrededor de 1,8 GiB de memoria y el servicio de inferencia continuó correctamente.
- **Hipótesis plausible:** presión de memoria, proceso de inicialización de MLflow y/o capacidad limitada de la instancia contribuyeron a los fallos temporales de acceso SSH.
- **No demostrado:** que exista OOM en el instante del incidente, que AWS fuera atacado, que Docker haya provocado el reinicio o que AWS Academy haya detenido el laboratorio por tiempo/budget. Las comprobaciones EC2 `2/2` no certifican disponibilidad del demonio SSH.
- **Pendiente:** revisar `journalctl -b -1` (arranque anterior), `journalctl -u ssh`, memoria y consumo de CPU por proceso, eventos EC2, estado y temporizador del Learner Lab, métricas CloudWatch/CPU credit balance, y compararlas con horas exactas del incidente.

## Decisión operativa y mitigaciones

1. **Mantener la API Docker** como servicio de consulta (`restart: unless-stopped`); ya superó smoke test dos veces y luego otra vez tras reinicio.
2. **Dejar MLflow Docker APAGADO por defecto**; cambiar su `restart` a `"no"` en Compose, conservar el perfil opcional `mlflow`. Activarlo manualmente solo durante administración y análisis, preferiblemente tras detener otras copias.
3. **Aplicar la política al contenedor existente** sin arrancarlo:
   ```bash
   sudo docker update --restart=no dsa-siniestralidad-mlflow-1
   ```
   En EC2, ya se ejecutó `docker compose --profile mlflow stop mlflow` y la API pasó el smoke test.
4. **No duplicar servicios pesados** en `t2.medium` de 4 GiB. Verificar consumo con `free -h`, `docker stats --no-stream` y `ps aux --sort=-rss | head` antes de levantar MLflow.
5. **Proteger estado fuera de la imagen:** datos aprobados `runtime/actualizaciones/activo`, modelo `runtime/serving/modelo_v2` y respaldo SQLite + artefactos `runtime/mlflow-docker`. Copiarlos a almacenamiento persistente independiente del laboratorio antes de migrar.
6. **Evitar cambios innecesarios en EC2:** nunca usar `docker compose --profile mlflow up -d` durante pruebas normales de la API; no reinstalar Docker ni repetir entrenamiento al recuperar acceso.
7. **Recuperación mínima:**
   ```bash
   cd ~/dsa-docker-build
   sudo docker compose ps -a
   python3 scripts/smoke_docker.py
   ```
   Si el API está `healthy` y el smoke test pasa, no reiniciar servicios.
8. **Escalamiento de infraestructura:** 8 GiB de RAM (`t3.large`, sujeto a disponibilidad/costo y restricciones Academy) solo si hay necesidad de coexistencia continua de MLflow/API y tras respaldos y medición. Más RAM no garantiza continuidad del laboratorio.

## Alcance de este registro

Esta nota preserva el problema, la evidencia y la mitigación para no repetir el tiempo de diagnóstico. No es un informe de incidente de seguridad ni un análisis de causa raíz definitivo. La aplicación sigue probada en Docker; **MLflow en su contenedor independiente aún requiere validar la lectura/carga del modelo desde su copia del Registry** antes de declarar completa esa parte del despliegue. El PR de Docker permanece en borrador hasta cerrar ese criterio o adoptar formalmente MLflow solo bajo demanda.
