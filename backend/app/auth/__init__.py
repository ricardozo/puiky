"""Autenticación de la interfaz web (Fase 5).

Dos tipos de llamante, como pide el diseño: el usuario humano (JWT de sesión
tras login) y el bot como servicio interno de confianza (token de servicio).
Ambos viajan como `Authorization: Bearer <token>`.
"""
