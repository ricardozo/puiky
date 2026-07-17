"""Cálculo de recurrencias para responsabilidades.

Gramática canónica de `recurrencia`:
  diaria | semanal | mensual | trimestral | anual | cada_<N>_dias

Se resuelve sin dependencias externas (suma manual de meses con ajuste de
fin de mes), para no añadir librerías ni reconstruir la imagen.
"""

import calendar
import re
from datetime import date, timedelta

_SIMPLES = {"diaria", "semanal", "mensual", "trimestral", "anual"}
_CADA_N = re.compile(r"^cada_(\d+)_dias$")


def es_recurrencia_valida(recurrencia: str) -> bool:
    if recurrencia in _SIMPLES:
        return True
    m = _CADA_N.match(recurrencia)
    return bool(m) and int(m.group(1)) > 0


def _sumar_meses(d: date, n: int) -> date:
    indice = d.month - 1 + n
    anio = d.year + indice // 12
    mes = indice % 12 + 1
    dia = min(d.day, calendar.monthrange(anio, mes)[1])  # ajusta 31 -> 30/28
    return date(anio, mes, dia)


def siguiente_vencimiento(desde: date, recurrencia: str) -> date:
    """Próximo vencimiento a partir de una fecha base y un patrón."""
    if recurrencia == "diaria":
        return desde + timedelta(days=1)
    if recurrencia == "semanal":
        return desde + timedelta(days=7)
    if recurrencia == "mensual":
        return _sumar_meses(desde, 1)
    if recurrencia == "trimestral":
        return _sumar_meses(desde, 3)
    if recurrencia == "anual":
        return _sumar_meses(desde, 12)
    m = _CADA_N.match(recurrencia)
    if m:
        return desde + timedelta(days=int(m.group(1)))
    raise ValueError(f"Recurrencia inválida: {recurrencia}")
