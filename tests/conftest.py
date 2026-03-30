"""Evita ruido en pytest: desactiva bloques bonitos de IA por defecto."""

import os

os.environ.setdefault("IA_CONSOLE_PRETTY", "false")
