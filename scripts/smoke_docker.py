"""Prueba de aceptación del contenedor paralelo: NO usa el puerto de producción.

Requiere el dataset aprobado de octubre 2026; no valida la exactitud futura
del modelo, solo la continuidad funcional de su inferencia y sus endpoints.
"""
import argparse
import json
import time
import urllib.error
import urllib.request


def obtener(base, endpoint):
    with urllib.request.urlopen(base + endpoint, timeout=45) as response:
        if response.status != 200:
            raise RuntimeError(f"{endpoint}: HTTP {response.status}")
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:18001")
    parser.add_argument("--corte-esperado", default="2026-10")
    parser.add_argument("--pronostico-esperado", default="2026-11")
    parser.add_argument("--publico", action="store_true")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    # Docker Compose marca el contenedor como Started antes de que MLflow
    # termine de cargar el modelo al iniciar Uvicorn.
    limite = time.monotonic() + 180
    while True:
        try:
            salud = obtener(base, "/health")
            break
        except (urllib.error.URLError, TimeoutError, ConnectionResetError) as exc:
            if time.monotonic() >= limite:
                raise RuntimeError(
                    "La API Docker no estuvo disponible en 180 segundos. "
                    "Verificar: sudo docker compose ps -a && "
                    "sudo docker compose logs --tail=80 api"
                ) from exc
            time.sleep(3)

    datos = obtener(base, "/api/estado-datos")
    forecast = obtener(base, "/api/pronostico")
    validacion = obtener(base, "/api/validacion")

    assert salud["status"] == "ok", salud
    assert datos["corte"] == args.corte_esperado, datos
    assert datos["localidades"] == 19, datos
    assert datos["filas"] == 2242, datos
    assert datos["dataset_actualizado"] is True, datos
    assert forecast["ultimo_mes_observado"] == args.corte_esperado, forecast
    assert forecast["periodo"] == args.pronostico_esperado, forecast
    assert forecast["numero_localidades"] == 19, forecast
    assert len(forecast["predicciones"]) == 19, forecast
    assert len(validacion["filas"]) == 228, validacion
    assert datos["modelo_servido"] == forecast["modelo"] == salud["modelo"]
    top = forecast["predicciones"][0]
    assert top["localidad"] == "KENNEDY", top
    if args.publico:
        with urllib.request.urlopen(base + "/", timeout=45) as response:
            assert 'data-publicacion="railway"' in response.read().decode("utf-8")
        for metodo, ruta in (
            ("GET", "/api/admin/estado"),
            ("POST", "/api/admin/preparar?corte=2026-10"),
            ("POST", "/api/admin/activar/prueba"),
        ):
            request = urllib.request.Request(base + ruta, method=metodo)
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    raise AssertionError(f"{metodo} {ruta}: HTTP {response.status}")
            except urllib.error.HTTPError as error:
                assert error.code == 404, (metodo, ruta, error.code)
        esquema = obtener(base, "/openapi.json")
        assert not any(ruta.startswith("/api/admin/") for ruta in esquema["paths"])
    print(json.dumps({
        "estado": "OK",
        "corte": datos["corte"],
        "filas": datos["filas"],
        "mes_proyectado": forecast["periodo"],
        "localidades": forecast["numero_localidades"],
        "modelo": forecast["modelo"],
        "primera_prioridad": top,
        "validacion_2024_filas": len(validacion["filas"]),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
