"""Estructuras de datos y lectura/escritura del JSON de letra (mismo formato que el generador automático)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple


@dataclass
class Verso:
    """Una línea de la letra con el momento (en segundos) en que se canta."""

    texto: str
    inicio: float
    fin: float
    pagina_nueva: bool = False
    fin_manual: bool = False  # el fin se marcó a mano (antes de un instrumental)

    @property
    def num_palabras(self) -> int:
        return len(self.texto.split())


@dataclass
class Pagina:
    """Grupo de 1 o 2 versos que se muestran juntos y se desplazan a la vez."""

    versos: List[Verso] = field(default_factory=list)

    @property
    def inicio(self) -> float:
        return self.versos[0].inicio

    @property
    def fin(self) -> float:
        return max(v.fin for v in self.versos)


def guardar_json(ruta, titulo: str, versos: List[Verso]) -> Path:
    registros = []
    for v in versos:
        registro = {"inicio": round(v.inicio, 3), "fin": round(v.fin, 3), "texto": v.texto}
        if v.pagina_nueva:
            registro["nueva_pagina"] = True
        if v.fin_manual:
            registro["fin_manual"] = True
        registros.append(registro)
    ruta = Path(ruta)
    ruta.write_text(
        json.dumps({"titulo": titulo, "marcado": "manual", "versos": registros}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ruta


def cargar_json(ruta) -> Tuple[str, List[Verso]]:
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    versos = []
    for i, v in enumerate(datos.get("versos", []), start=1):
        texto = str(v.get("texto", "")).strip()
        if not texto:
            raise ValueError(f"Verso {i} sin texto en {ruta}")
        inicio, fin = float(v["inicio"]), float(v["fin"])
        if fin < inicio:
            raise ValueError(f"Verso {i} ({texto!r}): 'fin' es menor que 'inicio'")
        versos.append(Verso(texto, inicio, fin, bool(v.get("nueva_pagina")), bool(v.get("fin_manual"))))
    versos.sort(key=lambda v: v.inicio)
    return str(datos.get("titulo", "")).strip(), versos
