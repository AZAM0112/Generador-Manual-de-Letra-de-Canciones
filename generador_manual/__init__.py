"""Generador MANUAL de videos de letras: tú marcas con ESPACIO cuándo empieza cada línea.

Uso como función:

    from generador_manual import marcar_cancion
    marcar_cancion("canciones/Mi canción.mp3", "canciones/Mi canción.txt")
"""
from __future__ import annotations

import re
import webbrowser
from pathlib import Path
from typing import Optional, Tuple, Union

from .letra import leer_archivo_letra
from .modelos import Verso, cargar_json, guardar_json

__all__ = ["marcar_cancion", "generar_video_desde_json", "titulo_desde_nombre", "cargar_json", "guardar_json", "Verso"]

Ruta = Union[str, Path]


def titulo_desde_nombre(audio: Ruta) -> str:
    """'01_cuan_grande_es_dios.mp3' -> 'Cuan Grande Es Dios'."""
    nombre = re.sub(r"^\d+[\s._-]+", "", Path(audio).stem)
    nombre = " ".join(nombre.replace("_", " ").split())
    return nombre.title() if nombre == nombre.lower() else nombre


def rutas_de_salida(audio: Path) -> Tuple[Path, Path]:
    """(video, json) junto al audio: 'Mi canción_letra.mp4' y 'Mi canción_letra.letra.json'."""
    video = audio.with_name(audio.stem + "_letra.mp4")
    return video, video.with_suffix(".letra.json")


def marcar_cancion(
    audio: Ruta,
    letra: Ruta,
    titulo: Optional[str] = None,
    *,
    abrir_navegador: bool = True,
    puerto: int = 0,
    resolucion: Tuple[int, int] = (1920, 1080),
    fps: int = 30,
    escala_letra: float = 1.0,
    fuente: Optional[str] = None,
    fondo: Tuple[int, int, int] = (0, 0, 0),
    al_iniciar=None,
) -> None:
    """Abre la página para marcar la letra y espera hasta que se cierre el programa.

    Al terminar de marcar se guardan `<audio>_letra.letra.json` y `<audio>_letra.mp4`.
    `al_iniciar(url)` se llama cuando el servidor está listo (útil para pruebas).
    """
    from .render import buscar_ffmpeg, duracion_audio
    from .servidor import Sesion, crear_servidor, url_de

    audio, letra = Path(audio), Path(letra)
    for ruta, que in ((audio, "el audio"), (letra, "la letra")):
        if not ruta.is_file():
            raise FileNotFoundError(f"No existe {que}: {ruta}")
    lineas = leer_archivo_letra(letra)
    video, ruta_json = rutas_de_salida(audio)
    sesion = Sesion(
        audio=audio, lineas=lineas, titulo=titulo or titulo_desde_nombre(audio),
        ruta_json=ruta_json, salida=video, duracion=duracion_audio(audio, buscar_ffmpeg()),
        opciones_video=dict(ancho=resolucion[0], alto=resolucion[1], fps=fps,
                            escala_letra=escala_letra, fuente=fuente, fondo=fondo),
    )
    servidor = crear_servidor(sesion, puerto)
    url = url_de(servidor)
    print(f"Canción: {audio.name}  ·  {len(lineas)} líneas de letra")
    print(f"Abriendo la página para marcar: {url}")
    print("(Para terminar el programa: botón «Cerrar programa» en la página, o Ctrl+C aquí.)")
    if abrir_navegador:
        webbrowser.open(url)
    if al_iniciar:
        al_iniciar(url)
    try:
        servidor.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    if sesion.estado.get("video"):
        print(f"Video: {sesion.estado['video']}")


def generar_video_desde_json(audio: Ruta, ruta_json: Optional[Ruta] = None, *, progreso=print, **opciones) -> Path:
    """Vuelve a generar el video con un JSON ya marcado (sin abrir la página)."""
    from .render import renderizar_video

    audio = Path(audio)
    video, por_defecto = rutas_de_salida(audio)
    titulo, versos = cargar_json(ruta_json or por_defecto)
    return renderizar_video(audio, video, titulo or titulo_desde_nombre(audio), versos, progreso=progreso, **opciones)
