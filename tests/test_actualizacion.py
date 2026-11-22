"""Pruebas aisladas de prevalidación de cargas, sin acceso a S3 ni MLflow."""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from siniestralidad.actualizacion import _armar_dataset, prevalidar_accidente


class PruebasActualizacion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.localidades = [f"LOCALIDAD {i:02d}" for i in range(19)]
        self.meses = pd.date_range("2016-01-01", "2025-12-01", freq="MS")
        base = [(local, mes) for local in self.localidades for mes in self.meses]
        self.referencia = self.dir / "dataset_vigente.csv"
        conteos = {(l, m): 1 for l, m in base}
        _armar_dataset(conteos, self.localidades, pd.Timestamp("2025-12-01")).to_csv(
            self.referencia, index=False
        )
        self.registros = [
            {"LOCALIDAD": l, "GRAVEDAD": "CON HERIDOS",
             "FECHA_OCURRENCIA_ACC": m.strftime("%Y-%m-%d")}
            for l, m in base
        ]
        self.origen = self.dir / "ACCIDENTE_nuevo.csv"

    def guardar(self, registros):
        pd.DataFrame(registros).to_csv(self.origen, index=False)

    def test_candidato_con_mes_nuevo_y_sin_modificar_historial(self):
        extra = [
            {"LOCALIDAD": l, "GRAVEDAD": "CON MUERTOS",
             "FECHA_OCURRENCIA_ACC": "2026-01-15"}
            for l in self.localidades
        ]
        self.guardar(self.registros + extra)
        df, reporte = prevalidar_accidente(
            self.origen, self.referencia, "2026-01", chunksize=73
        )
        self.assertEqual(reporte["estado"], "candidato_validado_pendiente_aprobacion")
        self.assertEqual(reporte["historial_modificado_filas"], 0)
        self.assertEqual(reporte["meses_nuevos"], {"2026-01": 19})
        self.assertEqual(len(df), 19 * 109)

    def test_bloquea_una_modificacion_historica(self):
        # Eliminamos un registro de enero de 2024, que sí está en el
        # dataset modelado de referencia (2017–2025). No eliminar uno
        # de enero de 2016: esa fila no altera sus conteos de 2017+.
        incompleto = [
            r for r in self.registros
            if not (
                r["LOCALIDAD"] == self.localidades[0]
                and r["FECHA_OCURRENCIA_ACC"] == "2024-01-01"
            )
        ]
        extra = [
            {"LOCALIDAD": l, "GRAVEDAD": "CON HERIDOS",
             "FECHA_OCURRENCIA_ACC": "2026-01-05"}
            for l in self.localidades
        ]
        self.guardar(incompleto + extra)
        _, reporte = prevalidar_accidente(
            self.origen, self.referencia, "2026-01", chunksize=121
        )
        self.assertEqual(reporte["estado"], "bloqueado_historial_inconsistente")
        self.assertEqual(reporte["historial_modificado_filas"], 1)

    def test_no_carga_mes_abierto(self):
        self.guardar(self.registros)
        with self.assertRaisesRegex(ValueError, "todavía no está cerrado"):
            prevalidar_accidente(self.origen, self.referencia, "2099-01")

    def test_no_acepta_fecha_de_corte_anterior(self):
        self.guardar(self.registros)
        with self.assertRaisesRegex(ValueError, "anterior al histórico vigente"):
            prevalidar_accidente(self.origen, self.referencia, "2025-11")


if __name__ == "__main__":
    unittest.main()
