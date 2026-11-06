"""Línea de comandos:  python -m generador_manual [audio.mp3] [letra.txt]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from . import generar_video_desde_json, marcar_cancion

EXTENSIONES_AUDIO = "*.mp3 *.wav *.m4a *.flac *.ogg *.aac"


def _elegir_archivo(titulo: str, tipos, carpeta: Path) -> Optional[Path]:
    """Ventana para elegir un archivo. Si no hay entorno gráfico, lo pide por la terminal."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        raiz = tk.Tk()
        raiz.withdraw()
        raiz.attributes("-topmost", True)
        ruta = filedialog.askopenfilename(title=titulo, filetypes=tipos, initialdir=str(carpeta), parent=raiz)
        raiz.destroy()
        return Path(ruta) if ruta else None
    except Exception:
        texto = input(f"{titulo} (ruta del archivo): ").strip().strip('"')
        return Path(texto) if texto else None


def _resolucion(texto: str):
    try:
        ancho, alto = texto.lower().split("x")
        return int(ancho), int(alto)
    except ValueError:
        raise argparse.ArgumentTypeError("usa el formato ANCHOxALTO, por ejemplo 1920x1080")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="marcar",
        description="Marca a mano (con ESPACIO) el inicio de cada línea de la letra y genera el video.",
    )
    p.add_argument("audio", nargs="?", help="audio de la canción (mp3, wav, m4a...). Si falta, se elige en una ventana")
    p.add_argument("letra", nargs="?", help="letra en .txt, una línea por parte. Por defecto, el .txt con el mismo nombre")
    p.add_argument("-t", "--titulo", help="título grande del inicio (por defecto, el nombre del archivo)")
    p.add_argument("--solo-video", action="store_true", help="no marca: rehace el video con el JSON ya guardado")
    p.add_argument("--no-abrir", action="store_true", help="no abre el navegador automáticamente")
    p.add_argument("--puerto", type=int, default=0, help="puerto local (por defecto, uno libre)")
    p.add_argument("--resolucion", type=_resolucion, default=(1920, 1080), metavar="ANCHOxALTO")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--tamano-letra", type=float, default=1.0, metavar="X", help="multiplica el tamaño de la letra")
    a = p.parse_args(argv)

    carpeta = Path("canciones") if Path("canciones").is_dir() else Path.cwd()
    audio = Path(a.audio) if a.audio else _elegir_archivo(
        "Elige el audio de la canción", [("Audio", EXTENSIONES_AUDIO), ("Todos", "*.*")], carpeta)
    if not audio:
        print("No se eligió ningún audio.", file=sys.stderr)
        return 1
    if not audio.is_file():
        print(f"Error: no existe el audio: {audio}", file=sys.stderr)
        return 1
    opciones = dict(resolucion=a.resolucion, fps=a.fps, escala_letra=a.tamano_letra)
    try:
        if a.solo_video:
            generar_video_desde_json(audio, ancho=a.resolucion[0], alto=a.resolucion[1], fps=a.fps,
                                     escala_letra=a.tamano_letra)
            return 0
        if a.letra:  # indicada a mano: si no existe es un error, no se pregunta
            letra = Path(a.letra)
        elif audio.with_suffix(".txt").is_file():  # el .txt con el mismo nombre que el audio
            letra = audio.with_suffix(".txt")
        else:
            letra = _elegir_archivo("Elige la letra (.txt)", [("Texto", "*.txt"), ("Todos", "*.*")], audio.parent)
        if not letra:
            print("No se eligió ninguna letra.", file=sys.stderr)
            return 1
        marcar_cancion(audio, letra, a.titulo, abrir_navegador=not a.no_abrir, puerto=a.puerto, **opciones)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
