"""Bases declarativas de los modelos ORM.

Dos metadatas separadas para el modelo multi-inquilino (schema por usuario):

- `ControlBase` — tablas de CONTROL, viven en el schema `public` y son
  compartidas por todos: `app_user`, `telegram_link`. Se migran aparte.
- `Base` — tablas de DOMINIO (notas, finanzas, tareas, …). Viven en el schema
  de cada inquilino (`t_<slug>`); se migran por schema. NO incluyen `app_user`.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Dominio. Se crea dentro del schema del inquilino según `search_path`."""


class ControlBase(DeclarativeBase):
    """Control. Vive en `public`, compartido entre inquilinos."""
