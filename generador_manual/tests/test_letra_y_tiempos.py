import tempfile
import unittest
from pathlib import Path

from generador_manual import titulo_desde_nombre
from generador_manual.letra import Linea, leer_archivo_letra, leer_letra
from generador_manual.modelos import Verso, cargar_json, guardar_json
from generador_manual.paginas import versos_a_paginas
from generador_manual.tiempos import construir_versos, duracion_estimada


class Letra(unittest.TestCase):
    def test_una_linea_por_parte_y_estrofas(self):
        lineas = leer_letra("[Verso 1]\nTu amor   me sostiene\nen la tormenta\n\n[Coro]\nJesús\n\n")
        self.assertEqual([l.texto for l in lineas], ["Tu amor me sostiene", "en la tormenta", "Jesús"])
        self.assertEqual([l.estrofa_nueva for l in lineas], [False, False, True])

    def test_lee_archivos_del_bloc_de_notas_antiguo(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "l.txt"
            ruta.write_bytes("Señor, ¿quién como tú?".encode("cp1252"))
            self.assertEqual(leer_archivo_letra(ruta)[0].texto, "Señor, ¿quién como tú?")

    def test_letra_vacia(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "l.txt"
            ruta.write_text("\n[Coro]\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                leer_archivo_letra(ruta)

    def test_titulo_desde_nombre(self):
        self.assertEqual(titulo_desde_nombre("01_cuan_grande_es_dios.mp3"), "Cuan Grande Es Dios")
        self.assertEqual(titulo_desde_nombre("TÓMALO - Hillsong.mp3"), "TÓMALO - Hillsong")


class Tiempos(unittest.TestCase):
    L = [Linea("Tu amor me sostiene"), Linea("en la tormenta"), Linea("Jesús", True)]

    def test_cada_linea_toma_su_marca_y_termina_antes_de_la_siguiente(self):
        versos = construir_versos(self.L, [2.0, 4.5, 30.0], duracion_audio=40)
        self.assertEqual([v.inicio for v in versos], [2.0, 4.5, 30.0])
        self.assertEqual(versos[0].fin, 4.5)  # no se pisa con la siguiente
        # Antes de un instrumental largo el texto no se queda todo el rato: fin estimado.
        self.assertAlmostEqual(versos[1].fin, 4.5 + duracion_estimada("en la tormenta"))
        self.assertTrue(versos[2].pagina_nueva)

    def test_fin_marcado_a_mano(self):
        versos = construir_versos(self.L, [2.0, 4.5, 30.0], {1: 8.0}, duracion_audio=40)
        self.assertEqual(versos[1].fin, 8.0)
        self.assertTrue(versos[1].fin_manual)

    def test_marcas_iguales_o_desordenadas_se_separan(self):
        versos = construir_versos(self.L, [2.0, 2.0, 1.0])
        inicios = [v.inicio for v in versos]
        self.assertEqual(inicios, sorted(inicios))
        self.assertGreater(inicios[1], inicios[0])

    def test_faltan_marcas(self):
        with self.assertRaisesRegex(ValueError, "Faltan marcar 1"):
            construir_versos(self.L, [2.0, None, 5.0])
        with self.assertRaises(ValueError):
            construir_versos(self.L, [2.0, 3.0])

    def test_la_ultima_linea_no_pasa_del_final_del_audio(self):
        versos = construir_versos(self.L, [2.0, 4.5, 39.5], duracion_audio=40)
        self.assertLessEqual(versos[-1].fin, 40)

    def test_json_ida_y_vuelta(self):
        versos = construir_versos(self.L, [2.0, 4.5, 30.0], {1: 8.0})
        with tempfile.TemporaryDirectory() as tmp:
            ruta = guardar_json(Path(tmp) / "x.letra.json", "Mi canción", versos)
            titulo, leidos = cargar_json(ruta)
        self.assertEqual(titulo, "Mi canción")
        self.assertEqual([(v.texto, v.inicio, v.fin_manual, v.pagina_nueva) for v in leidos],
                         [(v.texto, v.inicio, v.fin_manual, v.pagina_nueva) for v in versos])


class Paginas(unittest.TestCase):
    def test_maximo_dos_y_una_palabra_sola(self):
        versos = [Verso("uno dos", 0, 1), Verso("tres cuatro", 1, 2), Verso("cinco seis", 2, 3),
                  Verso("Jesús", 3, 4), Verso("siete ocho", 4, 5)]
        self.assertEqual([len(p.versos) for p in versos_a_paginas(versos)], [2, 1, 1, 1])


if __name__ == "__main__":
    unittest.main()
