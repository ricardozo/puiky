"""Capa NLU: traduce lenguaje natural a llamadas de las operaciones de negocio.

El proveedor del modelo es intercambiable (real = Ollama/Qwen OpenAI-compatible,
fake = intérprete determinista) para desarrollar en Windows sin el modelo y
ejecutar en Ubuntu con Qwen, sin tocar el código.
"""
