"""Canal de mensajería: bot de Telegram.

Capa desacoplada del resto. No contiene lógica de negocio: recibe mensajes de
Telegram (texto o voz), los pasa a la API de Puiky (capa NLU) y devuelve la
respuesta. Migrable a otro canal sin tocar el backend.
"""
