"""Pruebas del comportamiento temporal, modelo y ausencia de fugas."""
import unittest

import numpy as np
import pandas as pd

from siniestralidad.features import agregar_caracteristicas_v2, construir_siguiente_mes
from siniestralidad.modelo import ModeloOffset, VARIABLES_OFFSET


def panel_ficticio():
    meses = pd.date_range("2020-01-01", periods=25, freq="MS")
    filas = []
    for local in ("A", "B"):
        serie = np.arange(1, 26, dtype=float) + (20 if local == "B" else 0)
        for i, periodo in enumerate(meses):
            h = serie[:i]
            filas.append({
                "LOCALIDAD": local, "PERIODO": periodo, "SINIESTROS": serie[i],
                "MES": periodo.month, "ANIO": periodo.year,
                "MES_SIN": np.sin(2*np.pi*periodo.month/12),
                "MES_COS": np.cos(2*np.pi*periodo.month/12),
                "LAG_1": h[-1] if i else 20.,
                "LAG_3": h[-3] if i >= 3 else 20.,
                "LAG_6": h[-6] if i >= 6 else 20.,
                "LAG_12": h[-12] if i >= 12 else 20.,
                "MEDIA_MOVIL_3": h[-3:].mean() if i >= 3 else 20.,
                "MEDIA_MOVIL_6": h[-6:].mean() if i >= 6 else 20.,
                "MEDIA_MOVIL_12": h[-12:].mean() if i >= 12 else 20.,
                "PERIODO_2020_2021": int(periodo.year in (2020, 2021)),
            })
    return pd.DataFrame(filas)


class PruebasPipeline(unittest.TestCase):
    def test_mes_siguiente_sin_valores_futuros(self):
        original = panel_ficticio()
        p = construir_siguiente_mes(original)
        self.assertEqual(len(p), 2)
        self.assertEqual(p["PERIODO"].iloc[0], pd.Timestamp("2022-02-01"))
        esperado = original.query("LOCALIDAD == 'A'").iloc[-1]["SINIESTROS"]
        self.assertEqual(p.query("LOCALIDAD == 'A'")["LAG_1"].iloc[0], esperado)
        self.assertTrue(p["SINIESTROS"].isna().all())
        self.assertTrue(p["ESTACIONAL_CIUDAD"].notna().all())

    def test_panel_ya_enriquecido_como_el_de_fastapi(self):
        """Regresión: la API mantiene EWM_6 y ESTACIONAL_CIUDAD en df."""
        panel = panel_ficticio()
        previo = construir_siguiente_mes(panel)
        enriquecido = agregar_caracteristicas_v2(panel)
        nuevo = construir_siguiente_mes(enriquecido)
        self.assertEqual(len(nuevo), len(previo))
        self.assertIn("ESTACIONAL_CIUDAD", nuevo.columns)
        self.assertNotIn("ESTACIONAL_CIUDAD_x", nuevo.columns)
        self.assertNotIn("ESTACIONAL_CIUDAD_y", nuevo.columns)
        np.testing.assert_allclose(nuevo["ESTACIONAL_CIUDAD"], previo["ESTACIONAL_CIUDAD"])
        np.testing.assert_allclose(nuevo["EWM_6"], previo["EWM_6"])

    def test_no_permitir_saltos_de_mes(self):
        with self.assertRaises(ValueError):
            construir_siguiente_mes(panel_ficticio(), "2022-03-01")

    def test_estacionalidad_no_usa_periodo_actual(self):
        original = panel_ficticio()
        a = agregar_caracteristicas_v2(original)
        modificado = original.copy()
        modificado.loc[modificado["PERIODO"].eq(pd.Timestamp("2022-01-01")), "SINIESTROS"] *= 100
        b = agregar_caracteristicas_v2(modificado)
        antes = a.query("PERIODO == '2022-01-01'")["ESTACIONAL_CIUDAD"].to_numpy()
        despues = b.query("PERIODO == '2022-01-01'")["ESTACIONAL_CIUDAD"].to_numpy()
        np.testing.assert_allclose(antes, despues)

    def test_modelo_entrena_y_predice(self):
        x = agregar_caracteristicas_v2(panel_ficticio())
        modelo = ModeloOffset(min_samples_leaf=2, max_iter=20, max_leaf_nodes=3)
        modelo.fit(x[list(VARIABLES_OFFSET)], x["SINIESTROS"])
        p = modelo.predict(x[list(VARIABLES_OFFSET)])
        self.assertEqual(len(p), len(x))
        self.assertTrue(np.isfinite(p).all())
        self.assertTrue((p >= 0).all())


if __name__ == "__main__":
    unittest.main()
