"""Evita ruido en pytest: desactiva bloques bonitos de IA por defecto."""

import os

os.environ.setdefault("IA_CONSOLE_PRETTY", "false")
# Misma convención que producción: credenciales requeridas al arrancar Settings.
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_NAME", "recu_judicial")
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASSWORD", "postgres")
