"""Servidor local (solo en este computador) que muestra la página para marcar la letra,
reproduce el audio y, al terminar, guarda el JSON y genera el video."""
from __future__ import annotations

import json
import mimetypes
import re
import secrets
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .letra import Linea
from .modelos import cargar_json, guardar_json
from .tiempos import construir_versos

_PAGINA = Path(__file__).with_name("pagina.html")
_TIPOS_AUDIO = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac", ".wav": "audio/wav",
                ".flac": "audio/flac", ".ogg": "audio/ogg"}


@dataclass
class Sesion:
    audio: Path
    lineas: List[Linea]
    titulo: str
    ruta_json: Path
    salida: Path
    duracion: Optional[float] = None
    opciones_video: Dict = field(default_factory=dict)
    token: str = field(default_factory=lambda: secrets.token_urlsafe(16))
    estado: Dict = field(default_factory=lambda: {"fase": "marcando", "mensajes": [], "video": None, "error": None})
    _candado: threading.Lock = field(default_factory=threading.Lock)

    def marcas_previas(self) -> Tuple[Optional[List[float]], Dict[int, float]]:
        """Si ya existe un JSON de esta canción con las mismas líneas, sus tiempos."""
        if not self.ruta_json.exists():
            return None, {}
        try:
            _, versos = cargar_json(self.ruta_json)
        except (ValueError, KeyError, json.JSONDecodeError):
            return None, {}
        if [v.texto for v in versos] != [l.texto for l in self.lineas]:
            return None, {}  # la letra cambió: se empieza de cero
        return [v.inicio for v in versos], {i: v.fin for i, v in enumerate(versos) if v.fin_manual}

    def anotar(self, mensaje: str) -> None:
        with self._candado:
            self.estado["mensajes"] = (self.estado["mensajes"] + [mensaje])[-6:]

    def generar(self, titulo: str, inicios, fines: Dict[int, float]) -> None:
        """Guarda el JSON y genera el video (en otro hilo; el avance se consulta en /estado)."""
        versos = construir_versos(self.lineas, inicios, fines, self.duracion)
        with self._candado:
            if self.estado["fase"] == "generando":
                raise RuntimeError("Ya se está generando el video.")
            self.titulo = titulo.strip() or self.titulo
            guardar_json(self.ruta_json, self.titulo, versos)
            self.estado.update(fase="generando", mensajes=[f"Tiempos guardados en {self.ruta_json.name}"],
                               video=None, error=None)

        def trabajo():
            from .render import renderizar_video

            try:
                video = renderizar_video(self.audio, self.salida, self.titulo, versos,
                                         progreso=self.anotar, **self.opciones_video)
                with self._candado:
                    self.estado.update(fase="listo", video=str(video))
            except Exception as e:  # el error se muestra en la página
                with self._candado:
                    self.estado.update(fase="error", error=str(e))

        threading.Thread(target=trabajo, daemon=True).start()


def _abrir_carpeta(ruta: Path) -> None:
    if sys.platform == "win32":
        subprocess.Popen(["explorer", "/select,", str(ruta)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(ruta)])
    else:
        subprocess.Popen(["xdg-open", str(ruta.parent)])


def _crear_manejador(sesion: Sesion, al_cerrar):
    class Manejador(BaseHTTPRequestHandler):
        def log_message(self, *args):  # sin ruido en la terminal
            pass

        # -- respuestas -----------------------------------------------------------
        def _enviar(self, codigo, cuerpo: bytes, tipo: str, extra: Optional[Dict] = None):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(cuerpo)

        def _json(self, dato, codigo=HTTPStatus.OK):
            self._enviar(codigo, json.dumps(dato, ensure_ascii=False).encode("utf-8"),
                         "application/json; charset=utf-8")

        def _token_valido(self) -> bool:
            return secrets.compare_digest(self.headers.get("X-Token", ""), sesion.token)

        # -- GET ------------------------------------------------------------------
        def do_GET(self):
            ruta = self.path.split("?")[0]
            if ruta == "/":
                self._pagina()
            elif ruta == "/audio":
                self._audio()
            elif ruta == "/estado":
                with sesion._candado:
                    self._json(dict(sesion.estado))
            else:
                self._enviar(HTTPStatus.NOT_FOUND, b"No encontrado", "text/plain; charset=utf-8")

        do_HEAD = do_GET

        def _pagina(self):
            inicios, fines = sesion.marcas_previas()
            datos = {
                "titulo": sesion.titulo,
                "lineas": [{"texto": l.texto, "estrofa_nueva": l.estrofa_nueva} for l in sesion.lineas],
                "inicios": inicios,
                "fines": {str(k): v for k, v in fines.items()},
                "token": sesion.token,
                "audio": sesion.audio.name,
                "json": sesion.ruta_json.name,
            }
            html = _PAGINA.read_text(encoding="utf-8").replace(
                "__DATOS__", json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
            )
            self._enviar(HTTPStatus.OK, html.encode("utf-8"), "text/html; charset=utf-8")

        def _audio(self):
            """Envía el audio respetando los rangos pedidos (necesario para saltar dentro de él)."""
            tamano = sesion.audio.stat().st_size
            tipo = _TIPOS_AUDIO.get(sesion.audio.suffix.lower()) or mimetypes.guess_type(sesion.audio.name)[0] \
                or "application/octet-stream"
            rango = re.match(r"bytes=(\d*)-(\d*)$", self.headers.get("Range", "").strip())
            inicio, fin, codigo = 0, tamano - 1, HTTPStatus.OK
            if rango and (rango.group(1) or rango.group(2)):
                if rango.group(1):
                    inicio = int(rango.group(1))
                    fin = min(int(rango.group(2)), tamano - 1) if rango.group(2) else tamano - 1
                else:  # "bytes=-N": los últimos N bytes
                    inicio = max(0, tamano - int(rango.group(2)))
                if inicio >= tamano or inicio > fin:
                    self._enviar(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE, b"", tipo,
                                 {"Content-Range": f"bytes */{tamano}"})
                    return
                codigo = HTTPStatus.PARTIAL_CONTENT
            with open(sesion.audio, "rb") as f:
                f.seek(inicio)
                cuerpo = f.read(fin - inicio + 1)
            extra = {"Accept-Ranges": "bytes"}
            if codigo == HTTPStatus.PARTIAL_CONTENT:
                extra["Content-Range"] = f"bytes {inicio}-{fin}/{tamano}"
            self._enviar(codigo, cuerpo, tipo, extra)

        # -- POST -----------------------------------------------------------------
        def do_POST(self):
            if not self._token_valido():
                self._json({"error": "Petición no autorizada."}, HTTPStatus.FORBIDDEN)
                return
            largo = int(self.headers.get("Content-Length") or 0)
            try:
                cuerpo = json.loads(self.rfile.read(largo) or b"{}")
            except json.JSONDecodeError:
                self._json({"error": "Datos inválidos."}, HTTPStatus.BAD_REQUEST)
                return
            ruta = self.path.split("?")[0]
            if ruta == "/generar":
                try:
                    fines = {int(k): float(v) for k, v in (cuerpo.get("fines") or {}).items()}
                    sesion.generar(str(cuerpo.get("titulo", "")), cuerpo.get("inicios") or [], fines)
                except (ValueError, TypeError, RuntimeError) as e:
                    self._json({"error": str(e)}, HTTPStatus.BAD_REQUEST)
                    return
                self._json({"ok": True})
            elif ruta == "/abrir":
                if sesion.estado.get("video"):
                    _abrir_carpeta(Path(sesion.estado["video"]))
                self._json({"ok": True})
            elif ruta == "/cerrar":
                self._json({"ok": True})
                threading.Thread(target=al_cerrar, daemon=True).start()
            else:
                self._json({"error": "No encontrado."}, HTTPStatus.NOT_FOUND)

    return Manejador


def crear_servidor(sesion: Sesion, puerto: int = 0) -> ThreadingHTTPServer:
    """Servidor en 127.0.0.1 (no accesible desde otros equipos). Puerto 0 = uno libre."""
    servidor: Optional[ThreadingHTTPServer] = None

    def cerrar():
        servidor.shutdown()

    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), _crear_manejador(sesion, cerrar))
    servidor.daemon_threads = True
    return servidor


def url_de(servidor: ThreadingHTTPServer) -> str:
    return f"http://127.0.0.1:{servidor.server_address[1]}/"
