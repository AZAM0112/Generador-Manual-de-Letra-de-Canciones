"""De las marcas hechas con el teclado a versos con inicio y fin."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from .letra import Linea
from .modelos import Verso

SEPARACION_MINIMA = 0.05  # dos marcas no pueden caer en el mismo instante


def duracion_estimada(texto: str) -> float:
    """Cuánto suele durar cantar una línea: sirve para que el texto no quede en pantalla
    durante todo un instrumental cuando no se marcó su final."""
    return max(2.0, 0.6 * len(texto.split()) + 1.0)


def construir_versos(
    lineas: Sequence[Linea],
    inicios: Sequence[Optional[float]],
    fines: Optional[Dict[int, float]] = None,
    duracion_audio: Optional[float] = None,
) -> List[Verso]:
    """Une cada línea con su marca. Todas las líneas deben estar marcadas y en orden."""
    fines = fines or {}
    if len(inicios) != len(lineas):
        raise ValueError(f"Hay {len(lineas)} líneas pero llegaron {len(inicios)} marcas.")
    faltan = [i + 1 for i, t in enumerate(inicios) if t is None]
    if faltan:
        raise ValueError(f"Faltan marcar {len(faltan)} líneas (la primera es la {faltan[0]}).")
    tiempos = [max(0.0, float(t)) for t in inicios]
    for i in range(1, len(tiempos)):
        if tiempos[i] < tiempos[i - 1] + SEPARACION_MINIMA:
            tiempos[i] = tiempos[i - 1] + SEPARACION_MINIMA

    versos = []
    for i, (linea, inicio) in enumerate(zip(lineas, tiempos)):
        siguiente = tiempos[i + 1] if i + 1 < len(tiempos) else duracion_audio
        if i in fines and fines[i] > inicio:
            fin, manual = float(fines[i]), True
        else:
            fin, manual = inicio + duracion_estimada(linea.texto), False
        if siguiente is not None:
            fin = min(fin, max(siguiente, inicio + SEPARACION_MINIMA))
        versos.append(Verso(linea.texto, round(inicio, 3), round(max(fin, inicio + 0.3), 3),
                            pagina_nueva=linea.estrofa_nueva, fin_manual=manual))
    return versos
