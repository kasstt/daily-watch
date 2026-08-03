# -*- coding: utf-8 -*-
"""Que version del bot esta corriendo y que trae de nuevo.

Cuando aplico un parche, cambio estos dos valores.  El bot compara contra lo
que tiene guardado y, si no coinciden, te manda un aviso al chat.  Ese aviso
NO se borra solo: queda en el historial como comprobante de que el parche
entro y de que hay que probarlo.
"""

VERSION = "5.0"
FECHA = "03-08-2026"
TITULO = "ve el material escondido en JavaScript"

# Lo que cambio. Una linea por cosa, en criollo.
CAMBIOS = [
    "Ahora ve el material que la plataforma no enlaza y arma con JavaScript.",
    "Entra adentro de cada seccion del ramo y encuentra los archivos adjuntos.",
    "Ya no descarta los enlaces con ancla, que antes tiraba todos a la basura.",
    "Lee lo que cuelga de un onclick o de un atributo data-*.",
    "Si la pagina cambia y no puede decir que cambio, igual te avisa.",
    "Panel reordenado por uso, Pendientes primero.",
    "Tus mensajes se borran a los 5 segundos, no al instante.",
    "Boton de posponer 1 hora, ademas del de 3.",
]

# Que conviene probar despues de este parche, para hacer de tester.
A_PROBAR = [
    "Tocar Panel, Ramos, tu ramo, Ver material: tiene que listar algo.",
    "Tocar /revisar: tiene que contestar que miro.",
    "Esperar a que suban algo nuevo y ver si llega el aviso.",
]


def etiqueta():
    return "v%s" % VERSION
