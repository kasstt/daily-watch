# -*- coding: utf-8 -*-
# Prueba suelta: reproduce el caso real del usuario (busco "semana1.pdf").
import os
os.environ.setdefault("TG_TOKEN", "x")
os.environ.setdefault("TG_CHAT", "1")
import watcher as W

CASOS = [
    ("semana1.pdf", {"titulo": "Semana1.pdf", "url": "http://x/pluginfile/Semana1.pdf"}),
    ("semana1",     {"titulo": "Semana1.pdf", "url": "http://x/pluginfile/Semana1.pdf"}),
    ("Semana1.pdf", {"titulo": "Semana1.pdf", "url": "http://x/pluginfile/Semana1.pdf"}),
    ("semana 1",    {"titulo": "Semana1.pdf", "url": "http://x/pluginfile/Semana1.pdf"}),
    ("semana1.pdf", {"titulo": "Semana1", "url": "http://x/pluginfile/Semana1.pdf"}),
    ("semana1.pdf", {"titulo": "", "url": "http://x/pluginfile/Semana1.pdf"}),
]
for pedido, ficha in CASOS:
    print("%-14s vs %-12s -> %s" % (pedido, ficha["titulo"] or "(sin titulo)",
                                    W.calza_nombre(pedido, ficha)))
print("pelado('semana1.pdf') =", repr(W.pelado("semana1.pdf")))
print("pelado('Semana1.pdf') =", repr(W.pelado("Semana1.pdf")))
print("_sin_final('semana1.pdf') =", repr(W._sin_final("semana1.pdf")))
print("nombre_de_archivo (con extension en el enlace) =",
      repr(W.nombre_de_archivo(None, "http://x/pluginfile/Semana1.pdf")))
print("nombre_de_archivo (enlace mudo, con titulo) =",
      repr(W.nombre_de_archivo(None, "http://x/pluginfile/12345", "Semana 1")))
