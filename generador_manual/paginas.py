"""Reparto de los versos en páginas (lo que se ve junto en pantalla)."""
from __future__ import annotations

from typing import List

from .modelos import Pagina, Verso

MAX_VERSOS_PAGINA = 2  # máximo de versos en "lo que viene" (y en lo que se canta)
PAUSA_ESTROFA = 3.0  # silencio entre versos que obliga a empezar una página nueva


def versos_a_paginas(versos: List[Verso], max_versos: int = MAX_VERSOS_PAGINA) -> List[Pagina]:
    """Reparte los versos en páginas de hasta `max_versos`.

    Un verso de una sola palabra (el "Jesús" de un coro) va siempre solo en su página.
    También se abre página nueva al cambiar de estrofa (línea en blanco o [Coro] en la letra)
    o después de una pausa larga.
    """
    paginas: List[Pagina] = []
    actual: List[Verso] = []
    for v in versos:
        if actual:
            separada = (
                len(actual) >= max_versos
                or v.num_palabras == 1
                or actual[-1].num_palabras == 1
                or v.pagina_nueva
                or v.inicio - actual[-1].fin > PAUSA_ESTROFA
            )
            if separada:
                paginas.append(Pagina(actual))
                actual = []
        actual.append(v)
    if actual:
        paginas.append(Pagina(actual))
    return paginas
