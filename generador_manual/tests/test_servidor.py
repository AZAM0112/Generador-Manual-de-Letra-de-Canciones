import http.client
import json
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

from generador_manual.__main__ import main
from generador_manual.letra import leer_letra
from generador_manual.modelos import cargar_json, guardar_json
from generador_manual.servidor import Sesion, crear_servidor
from generador_manual.tiempos import construir_versos

LETRA = "Tu amor me sostiene\n\n[Coro]\nJesús\n¿Quién como tú?\n"


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg no instalado")
class Servidor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        carpeta = Path(self.tmp.name)
        self.audio = carpeta / "Mi canción.mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=300:duration=8",
                        "-b:a", "64k", str(self.audio)], check=True)
        self.sesion = Sesion(
            audio=self.audio, lineas=leer_letra(LETRA), titulo="Mi canción",
            ruta_json=carpeta / "Mi canción_letra.letra.json", salida=carpeta / "Mi canción_letra.mp4",
            duracion=8.0, opciones_video=dict(ancho=320, alto=180, fps=10),
        )
        self.servidor = crear_servidor(self.sesion)
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.addCleanup(self.servidor.server_close)
        self.addCleanup(self.servidor.shutdown)

    def pedir(self, metodo, ruta, cuerpo=None, cabeceras=None):
        c = http.client.HTTPConnection("127.0.0.1", self.servidor.server_address[1], timeout=10)
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        c.request(metodo, ruta, body=datos, headers=cabeceras or {})
        r = c.getresponse()
        return r.status, dict(r.getheaders()), r.read()

    def test_pagina_con_la_letra_y_el_token(self):
        estado, _, html = self.pedir("GET", "/")
        html = html.decode("utf-8")
        self.assertEqual(estado, 200)
        self.assertIn("¿Quién como tú?", html)
        self.assertIn(self.sesion.token, html)
        self.assertNotIn("__DATOS__", html)

    def test_audio_completo_y_por_rangos(self):
        tamano = self.audio.stat().st_size
        estado, cab, cuerpo = self.pedir("GET", "/audio")
        self.assertEqual((estado, len(cuerpo), cab["Content-Type"]), (200, tamano, "audio/mpeg"))
        self.assertEqual(cab["Accept-Ranges"], "bytes")
        estado, cab, cuerpo = self.pedir("GET", "/audio", cabeceras={"Range": "bytes=100-199"})
        self.assertEqual((estado, len(cuerpo)), (206, 100))
        self.assertEqual(cab["Content-Range"], f"bytes 100-199/{tamano}")
        self.assertEqual(cuerpo, self.audio.read_bytes()[100:200])
        estado, _, cuerpo = self.pedir("GET", "/audio", cabeceras={"Range": "bytes=-50"})
        self.assertEqual((estado, cuerpo), (206, self.audio.read_bytes()[-50:]))
        estado, _, _ = self.pedir("GET", "/audio", cabeceras={"Range": f"bytes={tamano + 10}-"})
        self.assertEqual(estado, 416)

    def test_sin_token_no_se_puede_generar(self):
        estado, _, _ = self.pedir("POST", "/generar", {"inicios": [1, 2, 3]})
        self.assertEqual(estado, 403)

    def test_marcas_incompletas_dan_error_claro(self):
        estado, _, cuerpo = self.pedir("POST", "/generar", {"titulo": "X", "inicios": [1.0, None, 3.0]},
                                       {"X-Token": self.sesion.token})
        self.assertEqual(estado, 400)
        self.assertIn("Faltan marcar", json.loads(cuerpo)["error"])

    def test_genera_json_y_video(self):
        estado, _, _ = self.pedir("POST", "/generar",
                                  {"titulo": "Título nuevo", "inicios": [1.0, 3.0, 5.5], "fines": {"1": 4.0}},
                                  {"X-Token": self.sesion.token})
        self.assertEqual(estado, 200)
        for _ in range(300):
            e = json.loads(self.pedir("GET", "/estado")[2])
            if e["fase"] != "generando":
                break
            time.sleep(0.1)
        self.assertEqual(e["fase"], "listo", e)
        self.assertTrue(Path(e["video"]).exists())
        titulo, versos = cargar_json(self.sesion.ruta_json)
        self.assertEqual(titulo, "Título nuevo")
        self.assertEqual([v.inicio for v in versos], [1.0, 3.0, 5.5])
        self.assertTrue(versos[1].fin_manual and versos[1].pagina_nueva)

    def test_recupera_marcas_previas_si_la_letra_no_cambio(self):
        guardar_json(self.sesion.ruta_json, "X", construir_versos(self.sesion.lineas, [1.0, 3.0, 5.5], {0: 2.0}))
        self.assertEqual(self.sesion.marcas_previas(), ([1.0, 3.0, 5.5], {0: 2.0}))
        self.sesion.lineas = leer_letra("Otra letra distinta\nJesús\nFin")
        self.assertEqual(self.sesion.marcas_previas(), (None, {}))


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg no instalado")
class LineaDeComandos(unittest.TestCase):
    def test_solo_video_con_json_guardado(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "c.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=duration=6", str(audio)],
                           check=True)
            guardar_json(Path(tmp) / "c_letra.letra.json", "C",
                         construir_versos(leer_letra("hola mundo\nadiós"), [1.0, 3.0], duracion_audio=6))
            codigo = main([str(audio), "--solo-video", "--resolucion", "320x180", "--fps", "10"])
            self.assertEqual(codigo, 0)
            self.assertTrue((Path(tmp) / "c_letra.mp4").exists())

    def test_audio_inexistente(self):
        self.assertEqual(main(["no_existe.mp3", "no_existe.txt", "--no-abrir"]), 1)


if __name__ == "__main__":
    unittest.main()
