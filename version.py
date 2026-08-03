# -*- coding: utf-8 -*-
"""Que version del bot esta corriendo.

Cada vez que se aplica un parche, el bot manda al chat un aviso con esta
lista.  Ese mensaje no se borra nunca: sirve de confirmacion de que la
actualizacion llego, y de lista para ir probando.
"""

VERSION = "5.1"
FECHA = "03-08-2026"
TITULO = "te manda los documentos aunque el enlace no diga la extension"

CAMBIOS = [
    "Ve el material escondido en JavaScript: antes la portada del ramo no",
    "  enlazaba nada y el bot la veia vacia. Ahora entra a cada seccion.",
    "Te manda el documento aunque el enlace no diga si es pdf, word, excel",
    "  o powerpoint. Le pregunta al servidor y le pone la extension correcta.",
    "Boton nuevo: Mandame los archivos. Te deja los documentos del ramo en",
    "  el chat sin que entres a la pagina.",
    "Ver material y Resumen ya no dicen lo mismo. Material es la lista",
    "  completa por tipo. Resumen es lo que entendio la IA.",
    "Si la IA no puede resumir, ahora te dice por que en una linea.",
    "El actualizador entiende la direccion del repositorio en cualquier",
    "  formato y te pregunta lo que falte, sin editar archivos a mano.",
]

A_PROBAR = [
    "Panel, Ramos, un ramo: fijate que aparezca el conteo de documentos.",
    "Toca Mandame los archivos y mira si te llegan al chat.",
    "Toca Ver material y despues Resumen con IA: tienen que ser distintos.",
]


def etiqueta():
    return "v%s (%s)" % (VERSION, TITULO)
