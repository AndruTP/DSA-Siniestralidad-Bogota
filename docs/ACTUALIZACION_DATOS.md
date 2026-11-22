# Actualización segura de ACCIDENTE.csv — Fase 1: prevalidación

## Restricciones

No ejecutar una carga de 237 MB desde una pestaña pública sin autenticación
administrativa, límite de tamaño, almacenamiento aislado y trabajos asíncronos.
Esta primera fase se ejecuta desde EC2, **sin modificar** el histórico, el DVC
de S3, MLflow ni FastAPI.

Se reutilizan las reglas principales de `preparar_dataset_dvc.py`: se filtran
las gravedades `CON HERIDOS` y `CON MUERTOS`, se agregan siniestros por
`LOCALIDAD` y mes, se mantienen 19 localidades (excluido Sumapaz), y se
construyen rezagos 1, 3, 6, 12 y medias 3, 6, 12.
A diferencia del script original, el mes de corte es configurable.

**Requisito del archivo:** es la **base acumulativa completa** desde 2016
hasta el último mes cerrado que se desea incorporar. Un archivo que contenga
solo los registros del último mes NO sirve para reemplazar el acumulado.

## Comprobar primero con la fuente antigua

```bash
cd ~/DSA-Siniestralidad-Bogota
source ~/.venv/bin/activate
python -m unittest discover -s tests -p 'test_actualizacion.py' -v

python -m siniestralidad.actualizacion_cli \
 --origen ACCIDENTE.csv --corte 2025-12 \
 --salida staging/dataset_modelado_prueba.csv \
 --reporte staging/auditoria_prueba.json
```

La prevalidación rechazará la publicación si detecta diferencias en conteos
históricos o localidades inválidas. **No supone que el último mes esté completo
por el hecho de tener registros**; se requiere confirmación externa del corte.

## Probar un archivo nuevo y acumulativo

Tras ubicar la fuente actualizada, por ejemplo `staging/ACCIDENTE_nuevo.csv`:

```bash
python -m siniestralidad.actualizacion_cli \
 --origen staging/ACCIDENTE_nuevo.csv --corte 2026-10 \
 --salida staging/dataset_modelado_candidato.csv \
 --reporte staging/reporte_actualizacion.json
```

El corte `2026-10` es un ejemplo: debe ajustarse al último mes
**confirmado como completo** por la fuente.

Se preserva la huella SHA-256 de la fuente y de la referencia y se generan
solo archivos en staging. El estado `candidato_validado_pendiente_aprobacion`
NO implica aprobación ni uso productivo.

## Próximas fases

1. Auditar cambios históricos legítimos (correcciones de SDM) y definir un
   proceso de aprobación explícito; no descartarlos silenciosamente.
2. Incorporar el candidato aprobado al versionado DVC/S3, en una transacción
   controlada con recuperación.
3. Adaptar el pipeline de reentrenamiento a ventanas temporales desplazables:
   hoy reproduce una evaluación fija 2017–2024.
4. Evaluar un nuevo modelo en una ventana reservada y compararlo con el vigente.
5. Publicar solo la versión aprobada y actualizar la fecha de corte leída
   por FastAPI. Las peticiones normales de pronóstico jamás reentrenan.
6. Crear la pestaña administrativa **con autenticación**, seguimiento de trabajos
   y límites de carga, nunca un endpoint abierto a Internet.

**Importante:** nuevas observaciones pueden modificar los registros históricos
por depuración de la fuente. El proceso actual los bloquea para revisión; no
declara que los datos corregidos sean erróneos.

## Limitaciones de la fase 1

La prevalidación no identifica duplicados a nivel de siniestro porque el
identificador único no se ha incorporado a la auditoría. Tampoco puede certificar
que los datos publicados por la SDM estén completos. No se han verificado aún
todas las variantes de fecha y codificación que podría traer un CSV actualizado.
