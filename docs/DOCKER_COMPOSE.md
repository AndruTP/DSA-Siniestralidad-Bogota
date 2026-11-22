# Despliegue paralelo de Docker en EC2 — DSA Siniestralidad Bogotá

## Objetivo y estado

Este es un **despliegue paralelo de prueba**, no una migración automática.
La aplicación original sigue en el puerto **8001**, y MLflow original sigue
en **8050**. Docker usa **18001** (API, únicamente loopback) y opcionalmente
**18050** (MLflow, únicamente loopback). No abrir estos puertos en el grupo de
seguridad ni exponer la administración sin autenticación.

Docker hace reproducible el despliegue y permite reinicios automáticos de
contenedores **si Docker está activo**, pero NO mantiene encendida una
instancia que AWS Academy detenga. El alojamiento permanente va aparte.

## Precondiciones

- Ubuntu EC2 Linux y Docker Engine con plugin Compose instalados.
- EC2 tiene el modelo V2 original accesible desde MLflow puerto 8050.
- Runtime original con el dataset **aprobado** en:
  `runtime/actualizaciones/activo/dataset_modelado.csv` (corte 2026-10).
- Respaldo de esos datos en almacenamiento duradero independiente de la EC2
  antes de despliegues definitivos.
- Imagen Python 3.14, MLflow 3.17.1, scikit-learn 1.9.1: verificar instalación
  y deserialización real en el entorno antes de cualquier reemplazo de producción.

No ejecutar `git reset --hard` ni `git clean -fd` en la EC2; el servidor
contiene archivos operativos no versionados. No tocar los modelos entrenados.

## Comandos de preparación (EC2)

Desde el repositorio, conservar el estado local y traer únicamente los archivos
de la rama de Docker.

```bash
cd ~/DSA-Siniestralidad-Bogota
source ~/.venv/bin/activate
git fetch origin

git restore --source=origin/feature/dsa-10-docker-compose -- \
  Dockerfile .dockerignore compose.yaml requirements-docker.txt \
  scripts/exportar_modelo_v2.py scripts/respaldar_mlflow_docker.py \
  scripts/smoke_docker.py docs/DOCKER_COMPOSE.md

# Utilizar versión API compatible con Docker sólo en la imagen:
# hacer copia antes de restaurar el archivo local (NO reiniciar API original).
cp api_dsa.py /tmp/api_dsa_ec2_operativa.py
git show origin/feature/dsa-10-docker-compose:api_dsa.py > /tmp/api_dsa_para_docker.py

# Descargar una copia VERIFICADA de MLflow V2 a volumen operativo.
python scripts/exportar_modelo_v2.py
```

**Importante:** la imagen debe contener la API de la rama Docker; para no
sobrescribir el archivo de EC2 basta con construir desde un **directorio de
staging separado**. El procedimiento recomendado es el siguiente:

```bash
mkdir -p ~/dsa-docker-build
git archive origin/feature/dsa-10-docker-compose | tar -x -C ~/dsa-docker-build
cd ~/dsa-docker-build
ln -s ~/DSA-Siniestralidad-Bogota/runtime runtime
docker compose build api
docker compose up -d api
```

La imagen se construye exclusivamente con archivos de GitHub; el enlace
simbólico `runtime` apunta al volumen persistente ya aprobado en la EC2.
`runtime` está excluido del contexto de imagen por `.dockerignore`.
**Requiere permisos de Docker para el usuario Ubuntu.**

## Prueba de aceptación sin interrumpir lo que funciona

```bash
cd ~/dsa-docker-build
docker compose ps
python3 scripts/smoke_docker.py
```

La prueba exige:
- API saludable.
- Corte 2026-10, 2242 registros y 19 localidades.
- Pronóstico 2026-11, 19 predicciones; Kennedy en primer lugar.
- 228 registros de validación 2024.

Para visualizar la versión Docker desde Windows, usar un **segundo túnel** SSH:

```powershell
ssh -N -i "$key" -L 8003:127.0.0.1:18001 ubuntu@IP_ACTUAL_EC2
```

Dashboard: `http://127.0.0.1:8003/`.

## MLflow en Docker (opcional después de confirmar la API)

MLflow original es un servidor separado y sigue disponible en 8050. Para
respaldar el tracking local en el directorio operativo:

```bash
cd ~/DSA-Siniestralidad-Bogota
source ~/.venv/bin/activate
python scripts/respaldar_mlflow_docker.py
```

En el directorio de build, opcionalmente:

```bash
cd ~/dsa-docker-build
docker compose --profile mlflow up -d mlflow
```

El backend SQLite y los artefactos se guardan fuera del contenedor en
`runtime/mlflow-docker`, de modo que sobreviven a reconstrucciones.
**No usar este MLflow clonado como fuente autorizada ni promocionar modelos
hasta comprobar que los paths de artefactos del Registry son resolubles**.

Para parar solamente el entorno Docker de prueba:

```bash
cd ~/dsa-docker-build
docker compose --profile mlflow down
```

Este comando NO detiene los servicios originales de los puertos 8001 y 8050.

## Precauciones

- La API sigue restringiendo `/api/admin/*` a `127.0.0.1`.
  `network_mode: host` mantiene esa característica en EC2 Linux; si se
  despliega tras un proxy inverso, hay que añadir autenticación real del lado
  servidor y probar el flujo de seguridad antes de exponer la administración.
- La imagen **no** incluye `ACCIDENTE.csv` crudo, credenciales AWS, el
  directorio `runtime` ni `mlflow.db` en la imagen.
- Para un hosting permanente, mover runtime/modelo/DB a volúmenes gestionados
  y proteger credenciales, además de configurar un dominio y HTTPS.
- El proceso usa `restart: unless-stopped`, válido mientras el host
  Docker Engine está activo. No impide que AWS Academy apague EC2.
- Si falla la carga del modelo o la imagen, consultar
  `docker compose logs --tail=80 api`; la aplicación original sigue intacta.
