# -*- coding: utf-8 -*-
"""Lee mis_datos.txt y lo convierte en variables de entorno.

Es solo para cuando corres el bot en tu computadora.  En GitHub no se usa:
alla los datos vienen de los Secrets del repositorio.

Este archivo NUNCA se sube: esta en .gitignore.
"""
import os

ARCHIVO = "mis_datos.txt"

CLAVES = [
    "SITE_A_URL", "SITE_A_USER", "SITE_A_PASS",
    "SITE_B_URL", "SITE_B_USER", "SITE_B_PASS",
    "CAL_URL",
    "CAL_URL_B",
    "TG_TOKEN", "TG_CHAT",
    "GH_TOKEN", "IA_KEY",
    # Claves de repuesto para los resumenes: si la primera se queda sin cupo,
    # el bot pasa sola a la siguiente.  Todas son opcionales.
    "IA_KEY_2", "IA_KEY_3", "IA_KEY_4", "IA_KEY_5", "IA_KEYS",
    "IA_KEY_2_PROVEEDOR", "IA_KEY_2_MODELO", "IA_KEY_2_URL",
    "GH_REPO",          # solo para el actualizador: usuario/repositorio
    "GH_RAMA",          # solo para el actualizador: casi siempre main
    "GIST_ID",          # opcional: si va vacio, el bot crea el gist solo
]


def cargar(ruta=None, silencioso=False):
    """Devuelve cuantos datos cargo.  No pisa lo que ya venga del sistema."""
    ruta = ruta or os.path.join(os.path.dirname(os.path.abspath(__file__)), ARCHIVO)
    if not os.path.isfile(ruta):
        if not silencioso:
            print("[i] no encontre %s, uso las variables del sistema" % ARCHIVO)
        return 0

    cargados = 0
    with open(ruta, encoding="utf-8-sig") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            nombre, _, valor = linea.partition("=")
            nombre, valor = nombre.strip(), valor.strip()
            if not nombre or not valor or valor.startswith("<"):
                continue
            if os.environ.get(nombre):
                continue
            os.environ[nombre] = valor
            cargados += 1

    if not silencioso:
        print("[i] cargue %d datos de %s" % (cargados, ARCHIVO))
    return cargados


def faltantes(obligatorias=None):
    obligatorias = obligatorias or ["TG_TOKEN", "TG_CHAT"]
    return [c for c in obligatorias if not os.environ.get(c, "").strip()]
