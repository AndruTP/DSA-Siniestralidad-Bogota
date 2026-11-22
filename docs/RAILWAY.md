# Publicación del dashboard en Railway

Usar un proyecto y un servicio nuevos en la cuenta del Taller 7. La rama de
publicación parte de `main` con el PR #20. El Dockerfile inicia Uvicorn en
`0.0.0.0:$PORT` al detectar `RAILWAY_PROJECT_ID`. Configurar `/health` con
300 segundos de espera en los ajustes de despliegue del servicio nuevo.

## Volumen y archivos aprobados

Montar un único volumen en `/app/runtime`. Su contenido debe incluir:

- `serving/modelo_v2/` completo, incluido `MLmodel` y los archivos de inferencia.
- `actualizaciones/activo/dataset_modelado.csv`.

Copiar desde un respaldo local verificado o descargar ambos elementos desde
EC2 por SFTP en modo de lectura. Comparar las huellas SHA-256 de origen y
destino. El directorio `runtime` se excluye de Git y del contexto de Docker.

Con la CLI de Railway autenticada, seleccionar explícitamente el proyecto,
entorno, servicio y volumen nuevos. Las rutas remotas de la CLI son relativas
a la raíz del volumen:

```text
railway volume files --volume <id-volumen> upload ./runtime/serving /serving
railway volume files --volume <id-volumen> upload ./runtime/actualizaciones /actualizaciones
railway volume files --volume <id-volumen> list /
```

En el segundo comando, usar una copia local que contenga únicamente
`activo/dataset_modelado.csv`. La API debe poder leer los archivos como usuario
`appuser`. Si la carga requiere un servicio activo, inicializar el volumen en el
mismo servicio con un comando temporal privado que mantenga vivo el contenedor.
Eliminar después el comando temporal para volver al arranque del Dockerfile
y configurar el healthcheck del servicio.

## Prueba antes de publicar

La aplicación exige el modelo local y el dataset con corte `2026-10`,
2.242 filas y 19 localidades al arrancar. Probar mediante un túnel al servicio
privado o con la misma imagen y el volumen montado localmente:

```text
python scripts/smoke_docker.py --base http://127.0.0.1:18001 --publico
```

La prueba comprueba el pronóstico de noviembre de 2026, la validación de 2024,
el HTML del tablero y la respuesta 404 de las operaciones administrativas.
Generar el dominio HTTPS del servicio nuevo después de la prueba y repetirla
con la URL pública.
