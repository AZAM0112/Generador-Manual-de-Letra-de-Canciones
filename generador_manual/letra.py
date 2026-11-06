"""Lectura de la letra (.txt): una línea = una parte que se marca con ESPACIO."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

_MARCADOR_SECCION = re.compile(r"^\s*[\[\(].*[\]\)]\s*$")  # [Coro], (Verso 1), ...


@dataclass
class Linea:
    texto: str
    estrofa_nueva: bool = False  # viene después de una línea en blanco o de un [Coro]


def leer_letra(texto: str) -> List[Linea]:
    """Cada línea con texto es una parte de la letra. Las líneas en blanco y los marcadores
    como [Coro] no se marcan: solo indican que empieza una estrofa (página nueva en el video)."""
    lineas: List[Linea] = []
    nueva = False
    for cruda in texto.splitlines():
        limpia = " ".join(cruda.split())
        if not limpia or _MARCADOR_SECCION.match(limpia):
            nueva = bool(lineas)
            continue
        lineas.append(Linea(limpia, nueva))
        nueva = False
    return lineas


def leer_archivo_letra(ruta) -> List[Linea]:
    ruta = Path(ruta)
    for codificacion in ("utf-8-sig", "cp1252"):  # el Bloc de notas antiguo guarda en cp1252
        try:
            lineas = leer_letra(ruta.read_text(encoding=codificacion))
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"No se pudo leer {ruta.name}: guárdalo como UTF-8.")
    if not lineas:
        raise ValueError(f"La letra {ruta.name} está vacía.")
    return lineas
