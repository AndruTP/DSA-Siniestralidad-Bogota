"""Prueba de aceptación del contenedor paralelo: NO usa el puerto de producción.

Requiere el dataset aprobado de octubre 2026; no valida la exactitud futura
del modelo, solo la continuidad funcional de su inferencia y sus endpoints.
"""
import argparse
import json
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
    args = parser.parse_args()
    base = args.base.rstrip("/")

    salud = obtener(base, "/health")
    datos = obtener(base, "/api/estado-datos")
    forecast = obtener(base, "/api/pronostico")
    validacion = obtener(base, "/api/validacion")

    assert salud["status"] == "ok", salud
    assert datos["corte"] == args.corte_esperado, datos
    assert datos["localidades"] == 19, datos\n    assert datos["filas"] == 2242, datos
    assert datos["dataset_actualizado"] is True, datos
    assert forecast["ultimo_mes_observado"] == args.corte_esperado, forecast
    assert forecast["periodo"] == args.pronostico_esperado, forecast
    assert forecast["numero_localidades"] == 19, forecast
    assert len(forecast["predicciones"]) == 19, forecast
    assert len(validacion["filas"]) == 228, validacion
    assert datos["modelo_servido"] == forecast["modelo"] == salud["modelo"]
    top = forecast["predicciones"][0]
    assert top["localidad"] == "KENNEDY", top
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
