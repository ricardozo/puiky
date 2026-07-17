"""Base declarativa común a todos los modelos ORM."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
